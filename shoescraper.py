from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import datetime
import re

def scrape_nike_shoes(url):
    total = 0
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

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Iterate over each shoe listing and extract relevant information
    for shoe_listing in shoe_listings:
        total = total + 1
        name = shoe_listing.find('div', class_='product-card__title').text.strip()
        brand = shoe_listing.find('div', class_='product-card__subtitle').text.strip()
        #Original price
        price_element = shoe_listing.select_one('[data-testid="product-price"]')
        if price_element:
            price_parts = price_element.text.strip().split("$")
            #takes everything but $
            original_price_str = price_parts[-1].strip()
            price = float(original_price_str)
        else:
            price = None

        #Reduced price
        reduced_price_element = shoe_listing.find('div', {'data-testid': 'product-price-reduced'})
        if reduced_price_element:
            reduced_price_parts = reduced_price_element.text.strip().split("$")
            #takes everything but $
            original_reduced_price_str = reduced_price_parts[-1].strip()
            reduced_price = float(original_reduced_price_str)
        else:
            reduced_price = None

        #discount
        if price is None or reduced_price is None:
            discount = None
        else:
            discount = round((price - reduced_price)/(price), 3)


        # Store shoe data in a dictionary
        shoe_data = {
            'name': name,
            'brand': brand,
            'prices': [{
                'price': price,
                'reduced_price': reduced_price,
                'timestamp': current_datetime,
                'discount': discount
            }]
        }

        shoes_data.append(shoe_data)
    print(str(total) + " shoes processed. Data scraped to nike_shoes.json.")
    return shoes_data

# Example usage
url = "https://www.nike.com/w/mens-shoes-nik1zy7ok"

data = scrape_nike_shoes(url)
with open("nike_shoes.json", "w") as file:
        json.dump(data, file, indent=4)
        