from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

# Initialize the Flask client app
app = Flask(__name__)
CORS(app)

# The URL of the main server.
SERVER_URL = 'http://localhost:5002/api/server'

@app.route('/api/client/ride-request', methods=['POST'])
def submit_ride_request():
    data = request.get_json()
    print(f"\n[Client API] Received request from Frontend: {data}")
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        print('[Client API] Forwarding request to main server...')
        server_response = requests.post(f'{SERVER_URL}/rides', json=data)
        
        response_data = server_response.json()
        print(f"[Client API] Received response from main server (Status: {server_response.status_code}): {response_data}")

        # Forward the exact response and status code from the main server
        return jsonify(response_data), server_response.status_code
        
    except requests.exceptions.ConnectionError:
        print(f"❌ [Client API] Cannot connect to the main server at {SERVER_URL}")
        return jsonify({'error': 'Unable to connect to the main ride server', 'server_url': SERVER_URL}), 503
        
    except Exception as e:
        print(f"❌ [Client API] An unexpected error occurred: {e}")
        return jsonify({'error': 'An internal error occurred in the Client API', 'details': str(e)}), 500

@app.route('/api/client/drivers/location/<driver_id>', methods=['GET'])
def get_driver_location(driver_id):
    try:
        print(f"[Client API] Requesting driver location for {driver_id} from main server...")
        server_response = requests.get(f'{SERVER_URL}/drivers/location/{driver_id}')
        
        response_data = server_response.json()
        print(f"[Client API] Received driver location response (Status: {server_response.status_code}): {response_data}")
        
        # Pass through the response from the main server
        return jsonify(response_data), server_response.status_code
        
    except requests.exceptions.ConnectionError:
        print(f"❌ [Client API] Cannot connect to the main server at {SERVER_URL}")
        return jsonify({'error': 'Unable to connect to the main ride server'}), 503
        
    except Exception as e:
        print(f"❌ [Client API] An unexpected error occurred: {e}")
        return jsonify({'error': 'Client API internal error', 'details': str(e)}), 500

if __name__ == '__main__':
    print('📦 Client-Facing API starting...')
    print('📡 Listening on http://localhost:5001 (This is the URL your frontend should use)')
    print(f'🔗 Forwarding requests to Main Server at: {SERVER_URL}')
    app.run(host='0.0.0.0', port=5001, debug=True)