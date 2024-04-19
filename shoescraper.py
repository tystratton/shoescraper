from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import datetime

def scrape_nike_shoes(url):
    with open("nike_shoes.json", "r") as file:
        data = json.load(file)
    processed = 0
    processed_new = 0
    shoes_data = []

    # Set up the browser
    driver = webdriver.Chrome()  # You can change this to your preferred browser driver
    driver.get(url)

    # Scroll down to the bottom of the page to load all content
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Adjust this value as needed
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Once all content is loaded, get the page source
    page_source = driver.page_source
    driver.quit()  # Close the browser

    # Use Beautiful Soup to parse the page source
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find all shoe listings on the page
    shoe_listings = soup.find_all('div', class_='product-card')

    # Iterate over each shoe listing and extract relevant information
    for shoe_listing in shoe_listings:
            processed = processed + 1
            name = shoe_listing.find('div', class_='product-card__title').text.strip()
            brand = shoe_listing.find('div', class_='product-card__subtitle').text.strip()
            available_color = shoe_listing.find('div', class_ = 'product-card__product-count').text.strip()
            href = shoe_listing.find('a', class_='product-card__link-overlay')['href']
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Original price
            price_element = shoe_listing.select_one('[data-testid="product-price"]')
            if price_element:
                price_parts = price_element.text.strip().split("$")
                #takes everything but $
                original_price_str = price_parts[-1].strip()
                price = float(original_price_str)
            else:
                price = None

            # Reduced price
            reduced_price_element = shoe_listing.find('div', {'data-testid': 'product-price-reduced'})
            if reduced_price_element:
                reduced_price_parts = reduced_price_element.text.strip().split("$")
                #takes everything but $
                original_reduced_price_str = reduced_price_parts[-1].strip()
                reduced_price = float(original_reduced_price_str)
            else:
                reduced_price = None

            # Discount
            if price is None or reduced_price is None:
                discount = None
            else:
                discount = round((price - reduced_price)/(price), 3)

            # Find if HREF is in code
            found = False
            for item in data:
                if item["href"] == href:
                    found = True
                    break

            # Append the new price, reduced price, and timestamp to the existing lists
            if found == True:
                item["price"].append(price)
                item["reduced_price"].append(reduced_price)
                item["timestamp"].append(current_datetime)

            # Create an entry if the product doesn't exist in the .json file
            else:
                processed_new = processed_new + 1
                data.append({
                    'name': name,
                    'brand': brand,
                    'available_color': available_color,
                    'href': href,
                    'price': [price],  # Start a new list for price
                    'reduced_price': [reduced_price],  # Start a new list for reduced price
                    'discount': [discount],
                    'timestamp': [current_datetime]  # Start a new list for timestamp
                })
    
    print(str(processed) + " shoes processed.")
    print(str(processed_new) + " new entries.")
    print("Data scraped to test.json.")
    with open("nike_shoes.json", "w") as file:
        json.dump(data, file, indent=4)

# Example usage
url = "https://www.nike.com/w/shoes-y7ok"
data = scrape_nike_shoes(url)
