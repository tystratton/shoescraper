import pandas as pd
import matplotlib.pyplot as plt
import json
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Load the JSON data from the file
with open('nike_shoes.json', 'r') as f:
    data = json.load(f)

# Convert JSON data to a pandas DataFrame
df = pd.DataFrame(data)

# Create a function to filter the data based on date range
def filter_by_date(df_expanded, date_filter):
    now = datetime.now()

    if date_filter == "Last 24 Hours":
        start_date = now - timedelta(days=1)
    elif date_filter == "Last Week":
        start_date = now - timedelta(weeks=1)
    elif date_filter == "Last Month":
        start_date = now - timedelta(weeks=4)
    else:
        return df_expanded  # No filtering if no option is selected

    # Filter the DataFrame to include only dates greater than or equal to start_date
    return df_expanded[df_expanded['timestamp'] >= start_date]

# Create a function to plot price over time inside tkinter
def plot_price_over_time(shoe_name, date_filter):
    # Filter the data for the selected shoe
    selected_shoe = df[df['name'] == shoe_name].iloc[0]

    # Create a DataFrame with timestamp and price columns
    df_expanded = pd.DataFrame({
        'timestamp': selected_shoe['timestamp'],
        'price': selected_shoe['price']
    })

    # Convert timestamp to datetime
    df_expanded['timestamp'] = pd.to_datetime(df_expanded['timestamp'])

    # Apply date filter
    df_filtered = filter_by_date(df_expanded, date_filter)

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        df_filtered['timestamp'], 
        df_filtered['price'], 
        marker='o', 
        linestyle='--', 
        linewidth=2, 
        markersize=8, 
        color='royalblue'
    )

    # Add labels and title
    ax.set_xlabel('Timestamp', fontsize=12)
    ax.set_ylabel('Price ($)', fontsize=12)
    ax.set_title(f'Price Over Time: {shoe_name} ({date_filter})', fontsize=16, fontweight='bold')

    # Add grid
    ax.grid(True, linestyle='--', alpha=0.6)

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')

    # Clear previous plot
    for widget in plot_frame.winfo_children():
        widget.destroy()

    # Display the plot in the tkinter window using FigureCanvasTkAgg
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Function to update the Listbox with matching shoe names as the user types
def update_shoe_listbox(event):
    search_text = shoe_entry.get().lower()
    matching_shoes = [name for name in shoe_names if search_text in name.lower()]
    shoe_listbox.delete(0, tk.END)
    for shoe in matching_shoes:
        shoe_listbox.insert(tk.END, shoe)

# Function to select a shoe from the Listbox
def on_shoe_select(event):
    selected_shoe.set(shoe_listbox.get(tk.ACTIVE))

# Function that gets triggered when "Plot Price Over Time" button is clicked
def on_plot_button_click():
    shoe_name = selected_shoe.get()
    date_filter = selected_filter.get()
    if shoe_name and date_filter:
        plot_price_over_time(shoe_name, date_filter)

# Create the main UI window
root = tk.Tk()
root.title("Shoe Price Tracker")

# Set green-themed background colors
root.configure(bg="#e6f9e6")  # Light green background

# Create and configure a style
style = ttk.Style()
style.configure("TLabel", background="#e6f9e6", font=("Arial", 12))
style.configure("TEntry", padding=5)
style.configure("TButton", background="#66b266", foreground="white", font=("Arial", 10, "bold"))
style.configure("TCombobox", background="#b3e6b3")
style.configure("TListbox", background="#d9f2d9")

# Label for shoe search
label = ttk.Label(root, text="Type to search for a shoe:", style="TLabel")
label.pack(pady=10)

# Entry widget for typing the shoe name
shoe_entry = ttk.Entry(root, width=50, style="TEntry")
shoe_entry.pack(pady=5)

# Listbox to display matching shoes
shoe_listbox = tk.Listbox(root, height=8, width=50, bg="#d9f2d9", font=("Arial", 10))
shoe_listbox.pack(pady=5)

# Bind events to update the Listbox dynamically and select from it
shoe_entry.bind('<KeyRelease>', update_shoe_listbox)
shoe_listbox.bind('<<ListboxSelect>>', on_shoe_select)

# Shoe selection variable
shoe_names = df['name'].tolist()
selected_shoe = tk.StringVar()

# Label for date filter
filter_label = ttk.Label(root, text="Select a date filter:", style="TLabel")
filter_label.pack(pady=10)

# Create a dropdown menu for date filtering
date_filters = ["No Filter", "Last 24 Hours", "Last Week", "Last Month"]
selected_filter = tk.StringVar()
filter_dropdown = ttk.Combobox(root, textvariable=selected_filter, values=date_filters, style="TCombobox")
filter_dropdown.current(0)  # Default to "No Filter"
filter_dropdown.pack(pady=10)

# Frame for displaying the plot
plot_frame = tk.Frame(root, bg="#e6f9e6")
plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Button to plot the price graph for the selected shoe
button = ttk.Button(root, text="Plot Price Over Time", command=on_plot_button_click, style="TButton")
button.pack(pady=10)

# Run the UI loop
root.mainloop()
