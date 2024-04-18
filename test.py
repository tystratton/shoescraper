from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import datetime
import requests

def scrape_nike_shoes(url):
    total = 0
    shoes_data = []

    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

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
        print(price_element)
        if price_element:
            price_parts = price_element.text.strip().split("$")
            #takes everything but $
            original_price_str = price_parts[-1].strip()
            price = float(original_price_str)
        else:
            price = None
        #Reduced price
        reduced_price_element = shoe_listing.find('div', {'data-testid': 'product-price-reduced'})

        print(reduced_price_element)
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
            'price': price,
            'reduced price': reduced_price,
            'timestamp': current_datetime,
            'discount': discount
        }
        shoes_data.append(shoe_data)
    print(str(total) + " shoes processed. Data scraped to test.json.")
    return shoes_data

# Example usage
url = "https://www.nike.com/w/mens-shoes-nik1zy7ok"
data = scrape_nike_shoes(url)
with open("test", "w") as file:
        json.dump(data, file, indent=4)