from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SERVER_URL = 'http://localhost:5002/api/server'

@app.route('/api/driver/rides/pending', methods=['GET'])
def get_pending_rides():
    try:
        resp = requests.get(f'{SERVER_URL}/driver/rides/pending')
        return jsonify({'success': True, 'rides': resp.json().get('rides', [])}), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

@app.route('/api/driver/rides/accept/<int:order_id>/<string:driver_id>', methods=['POST'])
def accept_ride(order_id, driver_id):
    try:
        resp = requests.post(f'{SERVER_URL}/driver/rides/accept/{order_id}/{driver_id}')
        return jsonify({'success': True, 'server_response': resp.json()}), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

@app.route('/api/driver/location/<string:driver_id>/<int:order_id>', methods=['GET'])
def get_driver_location(driver_id, order_id):
    try:
        resp = requests.get(f'{SERVER_URL}/drivers/location/{driver_id}/{order_id}')
        return jsonify({'success': True, 'location_data': resp.json()}), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

if __name__ == '__main__':
    print('📦 Amazon Driver Client API starting...')
    app.run(host='0.0.0.0', port=5003, debug=True)