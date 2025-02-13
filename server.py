from flask import Flask, render_template, jsonify, request
import psycopg2
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

app = Flask(__name__)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Connect to your PostgreSQL database
DB_NAME = os.getenv("PG_DB")
DB_USER = os.getenv("PG_USER")
DB_PASSWORD = os.getenv("PG_PASSWORD")
DB_HOST = os.getenv("PG_HOST")

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port="5432"
)
cur = conn.cursor()

@app.route('/guide')
def guide():
    return render_template('guide.html')

@app.route('/')
def index():
    try:
        # Get missing counts for each field
        cur.execute("""
            SELECT 
                SUM(CASE WHEN name IS NULL THEN 1 ELSE 0 END) as name_missing,
                SUM(CASE WHEN brand IS NULL THEN 1 ELSE 0 END) as brand_missing,
                SUM(CASE WHEN available_color IS NULL THEN 1 ELSE 0 END) as color_missing,
                SUM(CASE WHEN url IS NULL THEN 1 ELSE 0 END) as url_missing,
                SUM(CASE WHEN p.original_price IS NULL THEN 1 ELSE 0 END) as price_missing
            FROM shoes s
            LEFT JOIN prices p ON s.id = p.shoe_id AND p.timestamp = (
                SELECT MAX(timestamp) 
                FROM prices 
                WHERE shoe_id = s.id
            )
        """)
        missing_counts = cur.fetchone()

        # Get total processed count
        cur.execute("SELECT COUNT(*) FROM shoes")
        total_processed = cur.fetchone()[0]

        # Get last check timestamp
        cur.execute("SELECT MAX(timestamp) FROM prices")
        last_check = cur.fetchone()[0]
        last_check = last_check.strftime('%Y-%m-%d %H:%M:%S') if last_check else 'Never'

        # Create status dictionary
        status = {
            'name': {'count': missing_counts[0], 'warning': False, 'danger': missing_counts[0] > 0},
            'brand': {'count': missing_counts[1], 'warning': False, 'danger': missing_counts[1] > 0},
            'color': {'count': missing_counts[2], 'warning': False, 'danger': missing_counts[2] > 0},
            'url': {'count': missing_counts[3], 'warning': False, 'danger': missing_counts[3] > 0},
            'price_wrapper': {'count': missing_counts[4], 'warning': False, 'danger': missing_counts[4] > 0}
        }

        return render_template('index.html', 
                            status=status, 
                            last_check=last_check,
                            total_processed=total_processed)
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}")
        return "Error loading pipeline health", 500

@app.route("/api/shoes", methods=["GET"])
def get_shoes():
    try:
        # Get query parameters
        name = request.args.get('name', '').replace(' ', '%20')
        type = request.args.get('type')
        discounted = request.args.get('discounted', 'false').lower() == 'true'
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        year = request.args.get('year')
        month = request.args.get('month')
        day = request.args.get('day')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = 50
        offset = (page - 1) * per_page
        
        # Base query
        query = """
            SELECT DISTINCT ON (s.id) 
                s.id, s.name, s.type, s.colorway_code, 
                p.original_price, p.reduced_price, p.discount, p.timestamp
            FROM shoes s
            JOIN prices p ON s.id = p.shoe_id
            WHERE 1=1
        """
        params = []
        
        # Add name filter with more flexible matching
        if name:
            # Split name into words for more flexible searching
            name_terms = name.replace('%20', ' ').split()
            for term in name_terms:
                query += " AND s.name ILIKE %s"
                params.append(f"%{term}%")
            
        if discounted:
            query += " AND p.discount IS NOT NULL AND p.discount > 0"
            
        # Add price filters
        if min_price:
            query += " AND p.original_price >= %s"
            params.append(min_price)
        if max_price:
            query += " AND p.original_price <= %s"
            params.append(max_price)
            
        # Add timestamp filters
        if year:
            query += " AND EXTRACT(YEAR FROM p.timestamp) = %s"
            params.append(int(year))
        if month:
            query += " AND EXTRACT(MONTH FROM p.timestamp) = %s"
            params.append(int(month))
        if day:
            query += " AND EXTRACT(DAY FROM p.timestamp) = %s"
            params.append(int(day))
            
        # Add type filter
        if type:
            query += " AND s.type ILIKE %s"
            params.append(f"%{type}%")
            
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT s.id) 
            FROM shoes s 
            JOIN prices p ON s.id = p.shoe_id 
            WHERE 1=1
        """
        count_params = []  # Separate params for count query
        
        # Add filters to both queries consistently
        if name:
            name_terms = name.replace('%20', ' ').split()
            for term in name_terms:
                count_query += " AND s.name ILIKE %s"
                count_params.append(f"%{term}%")
                
        if discounted:
            count_query += " AND p.discount IS NOT NULL AND p.discount > 0"
            
        if min_price is not None:
            count_query += " AND p.reduced_price >= %s"
            count_params.append(min_price)
            
        if max_price is not None:
            count_query += " AND p.reduced_price <= %s"
            count_params.append(max_price)
            
        # Add type filter to count query
        if type:
            count_query += " AND s.type ILIKE %s"
            count_params.append(f"%{type}%")
            
        # Execute count query with its own parameters
        cur.execute(count_query, count_params)
        total_count = cur.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page
        
        # Add ordering and pagination to main query
        query += """
            ORDER BY s.id, p.timestamp DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])
        
        cur.execute(query, params)
        shoes = cur.fetchall()
        
        if not shoes:
            return jsonify({
                "error": "No shoes found matching criteria",
                "status": 404
            }), 404
            
        # Convert to list of dictionaries
        result = [{
            "id": shoe[0],
            "name": shoe[1],
            "type": shoe[2],
            "colorway": shoe[3],
            "original_price": float(shoe[4]) if shoe[4] else None,
            "reduced_price": float(shoe[5]) if shoe[5] else None,
            "discount": float(shoe[6]) if shoe[6] else None,
            "last_updated": shoe[7].isoformat() if shoe[7] else None
        } for shoe in shoes]
        
        return jsonify({
            "status": 200,
            "count": len(result),
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
            "data": result
        })
        
    except Exception as e:
        logging.error(f"Error in get_shoes: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": 500
        }), 500

@app.route("/api/shoe/<int:shoe_id>/prices", methods=["GET"])
def get_shoe_prices(shoe_id):
    try:
        query = """
            SELECT 
                s.name,
                s.type,
                s.colorway_code,
                p.original_price,
                p.reduced_price,
                p.discount,
                p.timestamp
            FROM shoes s
            JOIN prices p ON s.id = p.shoe_id
            WHERE s.id = %s
            ORDER BY p.timestamp DESC
        """
        
        cur.execute(query, [shoe_id])
        prices = cur.fetchall()
        
        if not prices:
            return jsonify({
                "error": f"No shoe found with ID {shoe_id}",
                "status": 404
            }), 404
            
        result = {
            "name": prices[0][0],
            "type": prices[0][1],
            "colorway": prices[0][2],
            "price_history": [{
                "original_price": float(price[3]) if price[3] else None,
                "reduced_price": float(price[4]) if price[4] else None,
                "discount": float(price[5]) if price[5] else None,
                "timestamp": price[6].isoformat() if price[6] else None
            } for price in prices]
        }
        
        return jsonify({
            "status": 200,
            "data": result
        })
        
    except Exception as e:
        logging.error(f"Error in get_shoe_prices: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": 500
        }), 500

# Start the server
if __name__ == "__main__":
    app.run(debug=True, port=5000)