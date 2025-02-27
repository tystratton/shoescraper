# Sole Search API

A web application that monitors and analyzes shoe prices across different retailers. Built with Flask and PostgreSQL, this tool helps users track price changes, discounts, and historical pricing data for various shoe models.

## Features
- Real-time price monitoring
- Historical price tracking and analysis
- Price change notifications
- Detailed shoe information including colorways and brands
- RESTful API for data access
- Interactive dashboard showing pipeline health and data completeness

## Tech Stack
- **Backend**: Python/Flask
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript
- **Environment**: Python dotenv for configuration

## Getting Started
1. Clone the repository
2. Install PostgreSQL if not already installed
3. Create database: `createdb shoedata`
4. Import database: `psql -U postgres -d shoedata < backup.sql`
5. Create a `.env` file with your database credentials:
   ```
   PG_DB=shoedata
   PG_USER=postgres
   PG_PASSWORD=your_password
   PG_HOST=localhost
   ```
6. Install requirements: `pip install -r requirements.txt`
7. Run the server: `python server.py`
8. Visit `http://localhost:5000` in your browser

## API Endpoints
- `/` - Pipeline health
- `/guide` - Show different URL combinations for API
- `/api/shoes` - Get all shoes with filtering options
- `/api/shoe/<id>/prices` - Get price history for a specific shoe
- `/price-changes` - View all recorded price changes

## License
MIT
