#Nike Shoescraper Program
#Ty Stratton
#see requirements.txt for more info

##Variables
##--

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from datetime import datetime
import schedule
import psycopg2
import os
from dotenv import load_dotenv
import logging

load_dotenv()
# Load credentials from environment variables
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASSWORD = os.getenv("PG_PASSWORD")
DB_HOST = os.getenv("PG_HOST")

# Connect to PostgresSQL
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port="5432"
)
cursor = conn.cursor()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging configuration with logs directory
log_filename = os.path.join('logs', f"nike_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,  # Changed to INFO to capture both errors and info messages
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def setup_error_logging():
    if not logging.getLogger().handlers:
        log_filename = os.path.join('logs', f"nike_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        os.makedirs('logs', exist_ok=True)
        handler = logging.FileHandler(log_filename)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.ERROR)

# Add this at the start of any error logging
def log_error(message):
    if not any(isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers):
        setup_error_logging()
    logging.error(message)

def scrape_nike_shoes(url):
    processed = 0
    processed_new = 0
    processed_shoes = set()

    # Set up the browser with options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
    except Exception as e:
        log_error(f"Failed to initialize browser: {str(e)}")
        return processed, processed_new

    # Wait for initial content to load
    time.sleep(5)
    
    # Scroll to load all products
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait to load page
        time.sleep(5)
        
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # If heights are the same, it means we've reached the bottom
            break
        last_height = new_height
        print("Scrolling for more products...")

    print("Finished scrolling, getting page content...")
    page_source = driver.page_source
    driver.quit()

    # Use Beautiful Soup to parse the page source
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find all shoe listings on the page
    shoe_listings = soup.find_all('div', class_='product-card')
    print(f"Found {len(shoe_listings)} shoe listings")

    # Iterate over each shoe listing and extract relevant information
    for shoe_listing in shoe_listings:
        try:
            processed += 1
            
            # Extract data with error checking
            name_elem = shoe_listing.find('div', class_='product-card__title')
            brand_elem = shoe_listing.find('div', class_='product-card__subtitle')
            color_elem = shoe_listing.find('div', class_='product-card__product-count')
            url_elem = shoe_listing.find('a', class_='product-card__link-overlay')
            
            if not all([name_elem, brand_elem, color_elem, url_elem]):
                log_error(f"Missing data for shoe {processed}:")
                if not name_elem: log_error("Missing name element")
                if not brand_elem: log_error("Missing brand element")
                if not color_elem: log_error("Missing color element")
                if not url_elem: log_error("Missing URL element")
                continue
                
            name = name_elem.text.strip()
            brand = brand_elem.text.strip()
            available_color = color_elem.text.strip()
            url = url_elem['href']
            
            logging.info(f"\nProcessing shoe {processed}:")
            logging.info(f"Name: {name}")
            logging.info(f"Brand: {brand}")
            logging.info(f"Colors: {available_color}")
            logging.info(f"URL: {url}")
            
            try:
                # Extract colorway code from URL
                colorway_code = url.split('/')[-1]
                
                # Initialize price variables
                price = None
                reduced_price = None
                discount = None

                # Extract price information
                price_wrapper = shoe_listing.find('div', class_='product-card__price')
                
                if price_wrapper:
                    # Look for reduced (current) price first
                    reduced_price_elem = price_wrapper.find('div', {'data-testid': 'product-price-reduced'})
                    if reduced_price_elem:
                        reduced_price_text = reduced_price_elem.text.strip().replace('$', '')
                        try:
                            reduced_price = float(reduced_price_text)
                        except ValueError:
                            reduced_price = None
                    
                    # Look for original price
                    original_price_elem = price_wrapper.find('div', {'data-testid': 'product-price'})
                    if original_price_elem:
                        original_price_text = original_price_elem.text.strip().replace('$', '')
                        try:
                            price = float(original_price_text)
                        except ValueError:
                            price = None
                    
                    # If no reduced price found, the original price is the current price
                    if reduced_price is None and price is None:
                        current_price_elem = price_wrapper.find('div', {'class': 'product-price is--current-price'})
                        if current_price_elem:
                            current_price_text = current_price_elem.text.strip().replace('$', '')
                            try:
                                price = float(current_price_text)
                            except ValueError:
                                price = None

                    # Calculate discount if we have both prices
                    if price and reduced_price:
                        discount = round(((price - reduced_price) / price) * 100, 2)
                
                # Insert/update the shoe and get its ID
                cursor.execute("""
                    INSERT INTO shoes (name, brand, available_color, url, colorway_code)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name, colorway_code) DO UPDATE 
                    SET brand = EXCLUDED.brand,
                        available_color = EXCLUDED.available_color,
                        url = EXCLUDED.url
                    RETURNING id;
                """, (name, brand, available_color, url, colorway_code))
                
                shoe_id = cursor.fetchone()[0]
                
                # In the shoe processing loop:
                shoe_key = f"{name}_{colorway_code}"
                if shoe_key in processed_shoes:
                    print(f"Skipping duplicate shoe: {name} ({colorway_code})")
                    continue
                    
                processed_shoes.add(shoe_key)
                
                # Always insert the current price
                cursor.execute("""
                    INSERT INTO prices (shoe_id, original_price, reduced_price, discount)
                    VALUES (%s, %s, %s, %s)
                """, (shoe_id, price, reduced_price, discount))
                conn.commit()
                processed_new += 1
                
            except Exception as e:
                log_error(f"Database error: {str(e)}")
                conn.rollback()
                
        except Exception as e:
            log_error(f"Error processing shoe {processed}: {str(e)}")
            continue

    print(f"\nScraping Summary:")
    print(f"Total shoes found: {len(shoe_listings)}")
    print(f"Shoes processed: {processed}")
    print(f"New entries added: {processed_new}")

    return processed, processed_new

def run_scraper():
    start_time = time.time()
    try:
        nike_url = "https://www.nike.com/w/shoes-y7ok"
        processed, processed_new = scrape_nike_shoes(nike_url)
        
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        logging.info(f"Scrape completed - Processed: {processed}, New: {processed_new}, Time: {minutes}m {seconds}s")
        
    except Exception as e:
        log_error(f"Error during scrape: {str(e)}")

def start_scheduler():
    # Run once immediately when started
    run_scraper()
    
    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(run_scraper)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    print("Nike Shoe Scraper Scheduler Started")
    print("Will run every 30 minutes")
    print("Press Ctrl+C to stop")
    start_scheduler()
