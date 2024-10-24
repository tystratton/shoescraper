import json
import pandas as pd
from datetime import datetime, timedelta

# Load the JSON data
with open('nike_shoes.json', 'r') as f:
    data = json.load(f)

# Convert the data into a pandas DataFrame
df = pd.DataFrame(data)

# Helper function to calculate price change for a specific time period
def calculate_price_change(shoe, period_start):
    df_expanded = pd.DataFrame({
        'timestamp': shoe['timestamp'],
        'price': shoe['price']
    })
    
    # Convert timestamps to datetime format
    df_expanded['timestamp'] = pd.to_datetime(df_expanded['timestamp'])
    
    # Filter data for the specific time period
    filtered_data = df_expanded[df_expanded['timestamp'] >= period_start]
    
    if len(filtered_data) >= 2:
        # Calculate price change (difference between last and first price in the time period)
        price_change = filtered_data['price'].iloc[-1] - filtered_data['price'].iloc[0]
        return price_change
    else:
        return None  # Not enough data points for this period

# Function to find the shoe with the largest price change in a given period
def find_largest_price_change(period):
    now = datetime.now()
    period_start = now - period
    largest_change = None
    largest_change_shoe = None
    
    for i, shoe in df.iterrows():
        change = calculate_price_change(shoe, period_start)
        if change is not None and (largest_change is None or abs(change) > abs(largest_change)):
            largest_change = change
            largest_change_shoe = shoe['name']
    
    return largest_change_shoe, largest_change

# Define the time periods (last day, week, month)
one_day = timedelta(days=1)
one_week = timedelta(weeks=1)
one_month = timedelta(weeks=4)

# Find the shoe with the largest price change in the last day, week, and month
largest_change_day, change_day = find_largest_price_change(one_day)
largest_change_week, change_week = find_largest_price_change(one_week)
largest_change_month, change_month = find_largest_price_change(one_month)

# Print the results
print(f"Shoe with largest price change in the last day: {largest_change_day} (Change: {change_day})")
print(f"Shoe with largest price change in the last week: {largest_change_week} (Change: {change_week})")
print(f"Shoe with largest price change in the last month: {largest_change_month} (Change: {change_month})")
