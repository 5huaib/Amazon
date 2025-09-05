from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import psycopg2
import os

# Initialize the Flask server app
app = Flask(__name__)
# Enable CORS for cross-origin requests
CORS(app)

# Database configuration - Temporarily hardcoded for testing
# NOTE: In a production environment, you should use environment variables
DB_NAME = 'amazon_orders'
DB_USER = 'shuaib'  # <-- Hardcoded your username for this test
DB_PASS = ''      # <-- Assumed blank password, a common default
DB_HOST = 'localhost'
DB_PORT = '5432'

# In-memory list to simulate a database for now
# This is now a fallback, as we will use Postgres
orders = []

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ Database connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return None

# A simple health check endpoint for the server
@app.route('/api/server/health', methods=['GET'])
def server_health():
    """Checks the health of the Amazon Server API."""
    return jsonify({
        'status': 'Amazon Server API is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/server/orders', methods=['POST'])
def receive_order_request():
    """
    Receives an order request from the client and stores it in the database.
    """
    # Get JSON data from the request body
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Extract required fields from the request
    product_id = data.get('product_id')
    user_id = data.get('user_id')
    quantity = data.get('quantity')
    
    # Validate required fields
    if not product_id or not user_id or not quantity:
        return jsonify({
            'error': 'Missing required fields: product_id, user_id, or quantity'
        }), 400
    
    # Use Postgres to store the data
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orders (user_id, product_id, quantity)
                    VALUES (%s, %s, %s) RETURNING order_id;
                    """,
                    (user_id, product_id, quantity)
                )
                order_id = cur.fetchone()[0]
                conn.commit()
            print('\n📝 Data successfully stored in Postgres.')
            return jsonify({
                'success': True,
                'message': 'Order request submitted and received by the server',
                'data': {
                    'order_id': order_id,
                    'user_id': user_id,
                    'product_id': product_id,
                    'quantity': quantity
                }
            }), 201
        except (psycopg2.DatabaseError, Exception) as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            return jsonify({
                'success': False,
                'message': 'Failed to save order to database',
                'details': str(e)
            }), 500
        finally:
            conn.close()
    else:
        # Fallback to in-memory storage if database connection fails
        print("\n⚠️ Database connection failed. Falling back to in-memory storage.")
        new_order = {
            'id': len(orders) + 1,
            'user_id': user_id,
            'product_id': product_id,
            'quantity': quantity,
            'status': 'processing',
            'created_at': datetime.now().isoformat()
        }
        orders.append(new_order)
        print('\n📝 Data successfully stored in-memory.')
        return jsonify({
            'success': True,
            'message': 'Order request submitted and received by the server (in-memory fallback)',
            'data': new_order
        }), 201


@app.route('/api/server/orders', methods=['GET'])
def get_all_orders():
    """Returns all orders by querying the database."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM orders ORDER BY created_at DESC;")
                orders = cur.fetchall()
                column_names = [desc[0] for desc in cur.description]
                orders_list = [dict(zip(column_names, order)) for order in orders]
            return jsonify({'success': True, 'data': orders_list})
        except psycopg2.DatabaseError as e:
            print(f"❌ Database query failed: {e}")
            return jsonify({'success': False, 'message': 'Failed to retrieve orders from database'})
        finally:
            conn.close()
    else:
        # Fallback to in-memory storage if database connection fails
        return jsonify({'success': True, 'data': orders})

@app.route('/api/server/orders/user/<user_id>', methods=['GET'])
def get_user_orders(user_id):
    """Returns orders for a specific user by querying the database."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC;",
                    (user_id,)
                )
                user_orders = cur.fetchall()
                column_names = [desc[0] for desc in cur.description]
                orders_list = [dict(zip(column_names, order)) for order in user_orders]
            return jsonify({'success': True, 'data': orders_list})
        except psycopg2.DatabaseError as e:
            print(f"❌ Database query failed: {e}")
            return jsonify({'success': False, 'message': 'Failed to retrieve user orders from database'})
        finally:
            conn.close()
    else:
        # Fallback to in-memory storage if database connection fails
        user_orders = [order for order in orders if order['user_id'] == user_id]
        return jsonify({'success': True, 'data': user_orders})


if __name__ == '__main__':
    print('🛒 Amazon Server API starting...')
    print('📡 API endpoints available at:')
    print('   - POST http://localhost:5002/api/server/orders (submit new order)')
    print('   - GET  http://localhost:5002/api/server/orders (get all orders)')
    print('   - GET  http://localhost:5002/api/server/orders/user/<user_id> (get user-specific orders)')
    # Run the server app
    app.run(host='0.0.0.0', port=5002, debug=True)
