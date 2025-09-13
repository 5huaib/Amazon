from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import math
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# --- Database Connection Setup ---
# IMPORTANT: In a real application, use environment variables for these details.
DB_NAME = "amazon_orders"
DB_USER = "postgres"
DB_PASS = "" # Add your PostgreSQL password here if you have one
DB_HOST = "localhost"
DB_PORT = "5432"

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Could not connect to the database: {e}")
        return None

# --- Helper Functions ---

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    φ1, φ2 = math.radians(float(lat1)), math.radians(float(lat2))
    Δφ, Δλ = math.radians(float(lat2) - float(lat1)), math.radians(float(lon2) - float(lon1))
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_nearest_available_driver(user_coords):
    """Finds the nearest driver by querying the database."""
    conn = get_db_connection()
    if not conn:
        return None
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT driver_id, name, latitude, longitude, status FROM drivers WHERE status = 'available'")
        available_drivers = cur.fetchall()
    conn.close()

    if not available_drivers:
        return None

    # The haversine function needs tuples of floats for coordinates
    for driver in available_drivers:
        driver['coords'] = (float(driver['latitude']), float(driver['longitude']))

    nearest_driver = min(
        available_drivers, 
        key=lambda d: haversine(user_coords[0], user_coords[1], d['coords'][0], d['coords'][1])
    )
    return nearest_driver

def generate_otp():
    return str(random.randint(1000, 9999))

# --- API Endpoints ---

@app.route('/api/server/rides', methods=['POST'])
def receive_ride_request():
    data = request.get_json()
    source_location = data.get('source_location')
    dest_location = data.get('dest_location')
    contact_no = data.get('contact_no')
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')
    
    # Simple validation
    if not all([source_location, dest_location, contact_no, user_lat, user_lng]):
        return jsonify({'error': 'Missing required fields'}), 400

    user_coords = (user_lat, user_lng)
    assigned_driver = find_nearest_available_driver(user_coords)

    if not assigned_driver:
        return jsonify({'success': False, 'message': 'No available drivers found nearby.'}), 404

    # This destination lookup would ideally be a separate function or table
    # For now, we'll hardcode one for demonstration if needed, or assume it's provided.
    # In a real app, you'd get dest_lat/lng from a geocoding service.
    # We will use dummy values for now as they are required by the DB schema.
    dest_lat, dest_lng = (12.9716, 77.5946) # Dummy destination coords for Bengaluru

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        sql = """
            INSERT INTO rides (user_contact, source_location, dest_location, user_lat, user_lng, dest_lat, dest_lng, assigned_driver_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id;
        """
        cur.execute(sql, (
            contact_no, source_location, dest_location, user_lat, user_lng, 
            dest_lat, dest_lng, assigned_driver['driver_id']
        ))
        new_ride = cur.fetchone()
        conn.commit()
    conn.close()

    if not new_ride:
        return jsonify({'error': 'Failed to create ride request'}), 500

    return jsonify({
        'success': True,
        'message': 'Ride request submitted. Waiting for driver to accept.',
        'data': {
            'order_id': new_ride['order_id'],
            'driver_id': assigned_driver['driver_id'],
            'driver_details': assigned_driver,
        }
    }), 201

@app.route('/api/server/driver/rides/pending', methods=['GET'])
def get_pending_rides():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
        
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # We need to get the user coords from the rides table to show on the driver's map
        cur.execute("""
            SELECT 
                r.order_id, r.source_location, r.dest_location, r.assigned_driver_id as driver_id,
                ARRAY[r.user_lat, r.user_lng] as user_coords 
            FROM rides r 
            WHERE r.status = 'pending'
        """)
        pending_rides = cur.fetchall()
    conn.close()
    
    return jsonify({'success': True, 'rides': pending_rides})


@app.route('/api/server/driver/rides/accept/<int:order_id>/<string:driver_id>', methods=['POST'])
def accept_ride(order_id, driver_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    new_otp = generate_otp()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Start a transaction
            # 1. Update the driver's status to 'busy'
            cur.execute("UPDATE drivers SET status = 'busy' WHERE driver_id = %s AND status = 'available'", (driver_id,))
            if cur.rowcount == 0:
                conn.rollback()
                return jsonify({'success': False, 'message': 'Driver is not available or does not exist.'}), 400

            # 2. Update the ride status to 'in_transit' and set the OTP
            cur.execute(
                "UPDATE rides SET status = 'in_transit', otp = %s WHERE order_id = %s AND status = 'pending'",
                (new_otp, order_id)
            )
            if cur.rowcount == 0:
                conn.rollback()
                return jsonify({'success': False, 'message': 'Ride not found or already accepted.'}), 404
            
            # 3. Fetch ride details to return to the driver app
            cur.execute("""
                SELECT 
                    user_contact, source_location, 
                    ARRAY[user_lat, user_lng] as user_coords 
                FROM rides WHERE order_id = %s
            """, (order_id,))
            ride_details = cur.fetchone()
            ride_details['otp'] = new_otp # Add otp to the response

            conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({
        'success': True,
        'message': f'Ride {order_id} accepted by driver {driver_id}',
        'ride_details': ride_details
    })

@app.route('/api/server/drivers/location/<string:driver_id>/<int:order_id>', methods=['GET'])
def get_driver_location(driver_id, order_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get current driver and user locations from the DB
        cur.execute("SELECT latitude, longitude FROM drivers WHERE driver_id = %s", (driver_id,))
        driver_loc = cur.fetchone()
        cur.execute("SELECT user_lat, user_lng, status, otp FROM rides WHERE order_id = %s", (order_id,))
        ride_info = cur.fetchone()

    if not driver_loc or not ride_info:
        conn.close()
        return jsonify({"error": "Ride or driver not found"}), 404

    driver_lat, driver_lng = driver_loc['latitude'], driver_loc['longitude']
    user_lat, user_lng = ride_info['user_lat'], ride_info['user_lng']

    distance = haversine(driver_lat, driver_lng, user_lat, user_lng)

    # Simulate movement and update the database
    new_status = ride_info['status']
    if ride_info['status'] == 'in_transit':
        if distance < 50:  # Arrived
            new_status = 'arrived'
            with conn.cursor() as cur:
                cur.execute("UPDATE rides SET status = 'arrived' WHERE order_id = %s", (order_id,))
                conn.commit()
        else: # Move closer
            step = 0.15
            new_lat = float(driver_lat) + step * (float(user_lat) - float(driver_lat))
            new_lng = float(driver_lng) + step * (float(user_lng) - float(driver_lng))
            with conn.cursor() as cur:
                cur.execute("UPDATE drivers SET latitude = %s, longitude = %s WHERE driver_id = %s", (new_lat, new_lng, driver_id))
                conn.commit()
            driver_lat, driver_lng = new_lat, new_lng
    
    conn.close()
    
    return jsonify({
        "driver_id": driver_id,
        "status": new_status,
        "otp": ride_info.get("otp"),
        "latitude": float(driver_lat),
        "longitude": float(driver_lng)
    })

if __name__ == '__main__':
    # Make sure you've inserted the initial driver data into your database!
    print('🛒 Main Amazon Server API (Database Mode) starting...')
    app.run(host='0.0.0.0', port=5002, debug=True)