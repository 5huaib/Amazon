from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

# Initialize the Flask client app
app = Flask(__name__)
# Enable CORS for cross-origin requests
CORS(app)

# The URL of the Amazon server. We are changing this to port 5002.
SERVER_URL = 'http://localhost:5002/api/server'

# A simple health check endpoint for the client
@app.route('/api/client/health', methods=['GET'])
def client_health():
    """Checks the health of the Amazon Client API."""
    return jsonify({
        'status': 'Amazon Client API is running',
        'server_url': SERVER_URL,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/client/order-request', methods=['POST'])
def submit_order_request():
    """
    Receives an order request from Postman and forwards it to the server API.
    """
    # Get JSON data from the request body
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    # Extract required parameters
    product_id = data.get('product_id')
    user_id = data.get('user_id')
    quantity = data.get('quantity')
    
    # Validate required parameters
    if not product_id or not user_id or not quantity:
        return jsonify({
            'error': 'Missing required parameters: product_id, user_id, or quantity'
        }), 400
    
    try:
        print('📦 Amazon Client API: Processing order request...')
        print(f'🛒 Product ID: {product_id}')
        print(f'👤 User ID: {user_id}')
        print(f'🔢 Quantity: {quantity}')
        
        # Forward the request to the Amazon server
        server_response = requests.post(f'{SERVER_URL}/orders', json={
            'product_id': product_id,
            'user_id': user_id,
            'quantity': quantity
        })
        
        print('✅ Amazon Client API: Request forwarded to server successfully')
        
        return jsonify({
            'success': True,
            'message': 'Order request submitted via Amazon Client API',
            'client_timestamp': datetime.now().isoformat(),
            'server_response': server_response.json()
        })
        
    except requests.exceptions.ConnectionError:
        # Handle case where the server is not running
        return jsonify({
            'error': 'Unable to connect to the Amazon Server',
            'server_url': SERVER_URL
        }), 503
        
    except requests.exceptions.RequestException as e:
        # Handle any other request-related errors
        return jsonify({
            'error': 'Amazon Client internal error', 
            'details': str(e)
        }), 500

@app.route('/api/client/orders/<user_id>', methods=['GET'])
def get_user_orders(user_id):
    """Fetches a user's order history from the server."""
    try:
        print(f'🔍 Client API: Fetching orders for user {user_id}')
        
        server_response = requests.get(f'{SERVER_URL}/orders/user/{user_id}')
        
        return jsonify({
            'success': True,
            'message': 'Order history fetched via Amazon Client API',
            'user_id': user_id,
            'orders': server_response.json()['data']
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Unable to connect to the Amazon Server',
            'server_url': SERVER_URL
        }), 503
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Client API internal error',
            'details': str(e)
        }), 500

@app.route('/api/client/orders', methods=['GET'])
def get_all_orders():
    """Fetches all orders from the server."""
    try:
        print('🔍 Client API: Fetching all orders')
        
        server_response = requests.get(f'{SERVER_URL}/orders')
        
        return jsonify({
            'success': True,
            'message': 'All orders fetched via Amazon Client API',
            'orders': server_response.json()['data']
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            'error': 'Unable to connect to the Amazon Server',
            'server_url': SERVER_URL
        }), 503
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Client API internal error',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    print('📦 Amazon Client API starting...')
    print('📡 Client API endpoint for submitting orders:')
    print('   - POST http://localhost:5001/api/client/order-request')
    print(f'🔗 Connects to Amazon Server at: {SERVER_URL}')
    
    app.run(host='0.0.0.0', port=5001, debug=True)
