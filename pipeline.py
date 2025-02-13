#Nike Shoescraper Program
#Ty Stratton
#see requirements.txt for more info
"""
Variables
--------------------------------
Database Variables:
DB_NAME     - PostgreSQL database name from environment variable
DB_USER     - Database username from environment variable
DB_PASSWORD - Database password from environment variable
DB_HOST     - Database host address from environment variable
conn        - PostgreSQL database connection object
cursor      - Database cursor for executing queries

Scraper Variables:
processed       - Counter for total shoes processed in current scrape
processed_new   - Counter for new price entries added
processed_shoes - Set to track unique shoes in current scrape to prevent duplicates
url            - Nike shoes webpage URL being scraped
chrome_options  - Selenium Chrome browser configuration settings

Shoe Data Variables:
name            - Full name of the shoe
type            - Category of shoe (Mens, Womens, Kids, etc.)
available_color - Number of color variations available
colorway_code   - Unique identifier for specific shoe color variant
url            - Direct link to the shoe's product page
price          - Original/full price of the shoe
reduced_price   - Sale price if available, None if not on sale
discount       - Calculated percentage discount from original price

Logging:
log_filename   - Path and name of current log file with timestamp
"""

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
from logging.handlers import RotatingFileHandler
import random
from collections import defaultdict
import json

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

# Set up logging with rotation
log_filename = os.path.join('logs', f"nike_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
handler = RotatingFileHandler(log_filename, maxBytes=1024*1024, backupCount=5)  # 1MB per file, keep 5 files
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

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

def create_status_report(missing_counts, total_processed):
    status_report = {
        'name': {
            'warning': missing_counts['name'] >= 1,
            'danger': missing_counts['name'] >= 25,
            'count': missing_counts['name']
        },
        'brand': {
            'warning': missing_counts['brand'] >= 1,
            'danger': missing_counts['brand'] >= 25,
            'count': missing_counts['brand']
        },
        'color': {
            'warning': missing_counts['color'] >= 1,
            'danger': missing_counts['color'] >= 25,
            'count': missing_counts['color']
        },
        'url': {
            'warning': missing_counts['url'] >= 1,
            'danger': missing_counts['url'] >= 25,
            'count': missing_counts['url']
        },
        'price_wrapper': {
            'warning': missing_counts['price_wrapper'] >= 1,
            'danger': missing_counts['price_wrapper'] >= 25,
            'count': missing_counts['price_wrapper']
        }
    }
    
    # Write status report
    with open('scraper_status.json', 'w') as f:
        json.dump(status_report, f, indent=4)

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

    # Initialize counter for missing elements
    missing_counts = defaultdict(int)
    total_processed = 0

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
                if not name_elem: 
                    log_error("Missing name element")
                    missing_counts['name'] += 1
                if not brand_elem: 
                    log_error("Missing brand element")
                    missing_counts['brand'] += 1
                if not color_elem: 
                    log_error("Missing color element")
                    missing_counts['color'] += 1
                if not url_elem: 
                    log_error("Missing URL element")
                    missing_counts['url'] += 1
                continue
                
            name = name_elem.text.strip()
            
            # Skip gift cards
            if "Gift Card" in name:
                logging.info(f"Skipping gift card product: {name}")
                continue
            
            type = (brand_elem.text.strip()
                   .replace("'s", "s")      # Convert "Men's" to "Mens"
                   .replace("s'", "s")       # Convert "Kids'" to "Kids"
                   .replace("/", " ")        # Convert "Baby/Toddler" to "Baby Toddler"
                   .replace(" Shoes", "")    # Remove " Shoes" from the end
                   .replace("-", " ")        # Convert hyphens to spaces
                   .replace("(", "")         # Remove opening parentheses
                   .replace(")", "")         # Remove closing parentheses
                   .strip())                # Remove any extra spaces
            
            # Skip entries that are just "Shoes"
            if type == "Shoes":
                logging.info(f"Skipping generic 'Shoes' entry: {name}")
                continue
            
            available_color_text = color_elem.text.strip()
            available_color = int(available_color_text.split()[0])
            url = url_elem['href']
            
            logging.info(f"\nProcessing shoe {processed}:")
            logging.info(f"Name: {name}")
            logging.info(f"Type: {type}")
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
                
                if not price_wrapper: 
                    log_error("Missing price wrapper element")
                    missing_counts['price_wrapper'] += 1
                    continue
                    
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
                    INSERT INTO shoes (name, type, available_color, url, colorway_code, brand)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name, colorway_code) DO UPDATE 
                    SET type = EXCLUDED.type,
                        available_color = EXCLUDED.available_color,
                        url = EXCLUDED.url,
                        brand = EXCLUDED.brand
                    RETURNING id;
                """, (name, type, available_color, url, colorway_code, 'Nike'))
                
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

    # After processing all shoes, create status report
    create_status_report(missing_counts, processed)

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
    
    # Schedule to run every hour with random variance (±5 minutes)
    while True:
        # Sleep for 55-65 minutes (3300-3900 seconds)
        sleep_time = random.randint(3300, 3900)
        minutes = sleep_time // 60
        seconds = sleep_time % 60
        logging.info(f"Next scrape scheduled in {minutes} minutes and {seconds} seconds")
        time.sleep(sleep_time)
        run_scraper()

if __name__ == "__main__":
    print("Soul Search Starting")
    print("Will run approximately every hour")
    print("Press Ctrl+C to stop")
    start_scheduler()
