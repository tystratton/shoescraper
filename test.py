from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import datetime
import requests

def search(values, searchFor):
    for k in values:
        for v in values[k]:
            if searchFor in v:
                return True
    return False

def scrape_nike_shoes(url):
    with open("test.json", "r") as file:
        data = json.load(file)
        print(type(data))
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
            available_color = shoe_listing.find('div', class_ = 'product-card__product-count').text.strip()
            href = shoe_listing.find('a', class_='product-card__link-overlay')['href']

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

            #Discount
            if price is None or reduced_price is None:
                discount = None
            else:
                discount = round((price - reduced_price)/(price), 3)
    
            # if href not in data:
            for i in data:
                print(i)
                if href in i:
                    test = True
                    break
            if href in data["href"]:
                print("total: " + str(total))
                shoe_data = {
                    'name': name,
                    'brand': brand,
                    'available_color': available_color,
                    'href': href,
                    'price': [],
                    'reduced_price': [],
                    'timestamp': [],
                    'discount': []
                }

            shoe_data['price'].append(price)
            shoe_data['reduced_price'].append(reduced_price)
            shoe_data['timestamp'].append(current_datetime)
            shoe_data['discount'].append(discount)
            shoes_data.append(shoe_data)
        print(str(total) + " shoes processed. Data scraped to test.json.")
        return shoes_data



    # #Checking more information in HREF
    # print("Got everything we need 1 :)")
    # for shoe_data in shoes_data:
    #     response = requests.get(href)
    #     if response.status_code == 200:
    #         soup = BeautifulSoup(response.text, 'html.parser')

    #     #find listing on page    
    #     shoe_listings = soup.find_all('div', class_='product-card')
    #     color = shoe_listing.find('img', {'alt'})
    #     if color is None:
    #         color = None
    #     else:
    #         shoe_data['color'].append(color)
    #     shoes_data.append(shoe_data)
    # return shoes_data

# Example usage
url = "https://www.nike.com/w/mens-shoes-nik1zy7ok"
data = scrape_nike_shoes(url)
with open("test.json", "w") as file:
        json.dump(data, file, indent=4)