import requests
from bs4 import BeautifulSoup
import json
total = 0
def scrape_nike_shoes(url):
    total = 0
    shoes_data = []

    # Send a GET request to the URL
    response = requests.get(url)

    # Check if request was successful
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all shoe listings on the page
        shoe_listings = soup.find_all('div', class_='product-card')

        # Iterate over each shoe listing and extract relevant information
        for shoe_listing in shoe_listings:
            total = total + 1
            name = shoe_listing.find('div', class_='product-card__title').text.strip()
            brand = shoe_listing.find('div', class_='product-card__subtitle').text.strip()
            price = shoe_listing.find('div', class_='product-price').text.strip()
            # You can add more attributes like color, size, etc. if available

            # Store shoe data in a dictionary
            shoe_data = {
                'name': name,
                'brand': brand,
                'price': price
            }

            shoes_data.append(shoe_data)

    return shoes_data

# URL of Nike's shoe listings page
url = 'https://www.nike.com/w/mens-shoes-nik1zy7ok'

# Scrape Nike shoes
all_nike_shoes = scrape_nike_shoes(url)

# Save scraped shoe data to a JSON file
with open('nike_shoes.json', 'w') as json_file:
    json.dump(all_nike_shoes, json_file, indent=4)

print("Scraped shoe data has been saved to nike_shoes.json file.")
print(total)
print("HEY")