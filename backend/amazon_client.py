from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SERVER_URL = 'http://localhost:5002/api/server'

@app.route('/api/client/ride-request', methods=['POST'])
def ride_request():
    data = request.get_json()
    try:
        resp = requests.post(f'{SERVER_URL}/rides', json=data)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

@app.route('/api/client/ride-status/<int:order_id>', methods=['GET'])
def ride_status(order_id):
    try:
        resp = requests.get(f'{SERVER_URL}/rides/status/{order_id}')
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

@app.route('/api/client/drivers/location/<string:driver_id>/<int:order_id>', methods=['GET'])
def driver_location(driver_id, order_id):
    try:
        resp = requests.get(f'{SERVER_URL}/drivers/location/{driver_id}/{order_id}')
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Server unreachable', 'details': str(e)}), 503

if __name__ == '__main__':
    print('📦 Client-Facing API starting...')
    app.run(host='0.0.0.0', port=5001, debug=True)