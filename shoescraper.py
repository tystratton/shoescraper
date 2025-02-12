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
import json
import datetime
import schedule
import psycopg2
import os
from dotenv import load_dotenv
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

def scrape_nike_shoes(url):
    processed = 0
    processed_new = 0

    # Set up the browser with options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Wait for initial content to load
    time.sleep(2)
    
    # Scroll to load all products
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait to load page
        time.sleep(2)
        
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
                print(f"Missing data for shoe {processed}")
                print(f"name_elem: {name_elem}")
                print(f"brand_elem: {brand_elem}")
                print(f"color_elem: {color_elem}")
                print(f"url_elem: {url_elem}")
                continue
                
            name = name_elem.text.strip()
            brand = brand_elem.text.strip()
            available_color = color_elem.text.strip()
            url = url_elem['href']
            
            print(f"\nProcessing shoe {processed}:")
            print(f"Name: {name}")
            print(f"Brand: {brand}")
            print(f"Colors: {available_color}")
            print(f"URL: {url}")
            
            try:
                # Extract colorway code from URL
                colorway_code = url.split('/')[-1]  # Gets the last part of the URL (e.g., 'HV6425-100')
                
                print("\n=== SHOE PROCESSING DEBUG ===")
                print(f"Name: {name}")
                print(f"URL: {url}")
                print(f"Brand: {brand}")
                print(f"Available Colors: {available_color}")
                print(f"Colorway Code: {colorway_code}")
                
                # First insert/update the shoe and get its ID
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
                print(f"Shoe ID: {shoe_id}")
                
                # Initialize price variables
                price = None
                reduced_price = None

                # Extract price information
                price_wrapper = shoe_listing.find('div', class_='product-card__price')
                print(f"DEBUG - Price wrapper found: {price_wrapper is not None}")
                
                if price_wrapper:
                    print(f"DEBUG - Full price wrapper HTML:")
                    print(price_wrapper.prettify())
                    
                    # Look for reduced (current) price first
                    reduced_price_elem = price_wrapper.find('div', {'data-testid': 'product-price-reduced'})
                    if reduced_price_elem:
                        reduced_price_text = reduced_price_elem.text.strip().replace('$', '')
                        try:
                            reduced_price = float(reduced_price_text)
                            print(f"DEBUG - Found reduced price: ${reduced_price}")
                        except ValueError:
                            print(f"DEBUG - Could not convert reduced price: {reduced_price_text}")
                            reduced_price = None
                    
                    # Look for original price
                    original_price_elem = price_wrapper.find('div', {'data-testid': 'product-price'})
                    if original_price_elem:
                        original_price_text = original_price_elem.text.strip().replace('$', '')
                        try:
                            price = float(original_price_text)
                            print(f"DEBUG - Found original price: ${price}")
                        except ValueError:
                            print(f"DEBUG - Could not convert original price: {original_price_text}")
                            price = None
                    
                    # If no reduced price found, the original price is the current price
                    if reduced_price is None and price is None:
                        current_price_elem = price_wrapper.find('div', {'class': 'product-price is--current-price'})
                        if current_price_elem:
                            current_price_text = current_price_elem.text.strip().replace('$', '')
                            try:
                                price = float(current_price_text)
                                print(f"DEBUG - Found current price: ${price}")
                            except ValueError:
                                print(f"DEBUG - Could not convert current price: {current_price_text}")
                                price = None
                
                print(f"DEBUG - Final values - Price: ${price}, Reduced: ${reduced_price}")
                
                # Calculate discount
                if price is not None and reduced_price is not None:
                    discount = round((price - reduced_price)/(price), 3)
                else:
                    discount = None
                
                # Check existing prices for this shoe today
                cursor.execute("""
                    SELECT original_price, reduced_price, timestamp 
                    FROM prices 
                    WHERE shoe_id = %s 
                    AND timestamp::date = CURRENT_DATE
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (shoe_id,))
                
                existing_price = cursor.fetchone()
                if existing_price:
                    print(f"Found existing price record today:")
                    print(f"Original: ${existing_price[0]}, Reduced: ${existing_price[1]}")
                    print(f"Timestamp: {existing_price[2]}")
                    print(f"Current price values - Original: ${price}, Reduced: ${reduced_price}")
                    
                    # Only insert if price has changed
                    if existing_price[0] != price or existing_price[1] != reduced_price:
                        cursor.execute("""
                            INSERT INTO prices (shoe_id, original_price, reduced_price, discount)
                            VALUES (%s, %s, %s, %s)
                        """, (shoe_id, price, reduced_price, discount))
                        conn.commit()
                        print("Price changed - inserted new record")
                    else:
                        print("Price unchanged - skipping insert")
                else:
                    cursor.execute("""
                        INSERT INTO prices (shoe_id, original_price, reduced_price, discount)
                        VALUES (%s, %s, %s, %s)
                    """, (shoe_id, price, reduced_price, discount))
                    conn.commit()
                    print("No existing price today - inserted new record")
                
                print("=== END PROCESSING ===\n")
                
            except Exception as e:
                print(f"Database error: {str(e)}")
                conn.rollback()
                
        except Exception as e:
            print(f"Error processing shoe {processed}: {str(e)}")
            continue

    print(f"\nScraping Summary:")
    print(f"Total shoes found: {len(shoe_listings)}")
    print(f"Shoes processed: {processed}")
    print(f"New entries added: {processed_new}")


# Move your existing scraping code into a function
def run_scraper():
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\nStarting scrape at {current_time}")
    try:
        nike_url = "https://www.nike.com/w/shoes-y7ok"
        scrape_nike_shoes(nike_url)
        print("Scrape completed successfully")
    except Exception as e:
        print(f"Error during scrape: {str(e)}")

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
