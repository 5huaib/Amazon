from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import psycopg2
import random
import math

# Initialize the Flask server app
app = Flask(__name__)
CORS(app)

# Database configuration
DB_NAME = 'amazon_orders'
DB_USER = 'shuaib' # <--- CHANGE THIS TO YOUR POSTGRESQL USER
DB_PASS = ''       # <--- CHANGE THIS TO YOUR POSTGRESQL PASSWORD
DB_HOST = 'localhost'
DB_PORT = '5432'

# A list of prime locations in Bangalore
bangalore_locations = {
    "Koramangala": {"coords": (12.9345, 77.6186), "val": 5}, "Indiranagar": {"coords": (12.9784, 77.6408), "val": 10},
    "Jayanagar": {"coords": (12.9293, 77.5848), "val": 15}, "Rajajinagar": {"coords": (12.9972, 77.5502), "val": 20},
    "Basavanagudi": {"coords": (12.9416, 77.5752), "val": 25}, "Marathahalli": {"coords": (12.9567, 77.7011), "val": 30},
    "HSR Layout": {"coords": (12.9116, 77.6385), "val": 35}, "Whitefield": {"coords": (12.9699, 77.7508), "val": 40},
    "Electronic City": {"coords": (12.8466, 77.6657), "val": 45}, "JP Nagar": {"coords": (12.9063, 77.5844), "val": 50},
    "BTM Layout": {"coords": (12.9165, 77.6095), "val": 55}, "Malleshwaram": {"coords": (12.9986, 77.5684), "val": 60},
    "Hebbal": {"coords": (13.0381, 77.5913), "val": 65}, "Sarjapur Road": {"coords": (12.9234, 77.7027), "val": 70},
    "Banashankari": {"coords": (12.9268, 77.5513), "val": 75}, "Vasanth Nagar": {"coords": (12.9892, 77.5878), "val": 80},
    "Bellandur": {"coords": (12.9304, 77.6784), "val": 85}, "Yelahanka": {"coords": (13.1007, 77.5963), "val": 90},
    "Frazer Town": {"coords": (12.9959, 77.6124), "val": 95}, "Richmond Town": {"coords": (12.9649, 77.5954), "val": 100},
}

# Lists of names and car models for generating drivers
indian_names = ["Aarav", "Ayan", "Kabir", "Rohan", "Ananya", "Diya", "Mohammed", "Ali", "Fatima", "Aisha", "Ryan", "Kevin", "Sarah", "Harman", "Simran"]
car_models = ["Toyota Prius", "Honda Civic", "Ford Focus", "Hyundai Verna", "Tata Nexon", "Maruti Swift", "Mahindra XUV", "Renault Kwid"]

# Generate a pool of 200 drivers
drivers = []
for i in range(200):
    location_name = random.choice(list(bangalore_locations.keys()))
    drivers.append({
        "driver_id": f"D-{i+1:03d}", "name": random.choice(indian_names), "car_model": random.choice(car_models),
        "location_name": location_name, "coords": bangalore_locations[location_name]["coords"],
        "phone_number": f"987654{i:04d}", "vehicle_number": f"KA-01-AB-{i+1:04d}"
    })

# In-memory store for tracking active rides
active_rides = {}

def find_nearest_driver(user_location_name):
    user_location_val = bangalore_locations.get(user_location_name, {}).get("val")
    if user_location_val is None:
        print(f"❌ Invalid user location name: {user_location_name}")
        return {"error": "Invalid source location provided."}
    
    # MODIFIED: Increased the search radius to make it much easier to find a driver.
    # The original value of 3 was too small and often found no drivers.
    distance_threshold = 25
    
    print(f"\nSearching for drivers near '{user_location_name}' (val={user_location_val}) with threshold={distance_threshold}...")
    
    nearby_drivers = []
    for driver in drivers:
        # Do not assign a driver who is already on an active ride
        if any(ride.get("driver_id") == driver["driver_id"] for ride in active_rides.values()):
            continue
        
        driver_location_val = bangalore_locations.get(driver['location_name'], {}).get("val")
        if driver_location_val is not None:
            distance = abs(user_location_val - driver_location_val)
            if distance <= distance_threshold:
                nearby_drivers.append((driver, distance))

    if not nearby_drivers:
        print("❌ No available drivers found within the threshold.")
        return {"error": "We're sorry, all our drivers are currently busy. Please try again in a few moments."}
    
    # Sort by distance to find the absolute closest driver in the found group
    nearby_drivers.sort(key=lambda x: x[1])
    nearest_driver = nearby_drivers[0][0]
    
    print(f"✅ Found {len(nearby_drivers)} drivers. Assigning the closest one: {nearest_driver['name']} at {nearest_driver['location_name']}")
    return nearest_driver

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ, Δλ = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def generate_waypoints(start_coords, end_coords, num_waypoints=3):
    waypoints = [start_coords]
    lat_diff, lon_diff = end_coords[0] - start_coords[0], end_coords[1] - start_coords[1]
    for i in range(1, num_waypoints + 1):
        fraction = i / (num_waypoints + 1)
        lat = start_coords[0] + lat_diff * fraction + random.uniform(-0.002, 0.002)
        lon = start_coords[1] + lon_diff * fraction + random.uniform(-0.002, 0.002)
        waypoints.append((lat, lon))
    waypoints.append(end_coords)
    return waypoints

def generate_otp():
    return str(random.randint(1000, 9999))

def get_db_connection():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        print("✅ Database connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
        return None

@app.route('/api/server/rides', methods=['POST'])
def receive_ride_request():
    data = request.get_json()
    print(f"\nReceived ride request from Client API: {data}")
    
    if not data: return jsonify({'error': 'No data provided'}), 400
    
    source_location, dest_location, contact_no = data.get('source_location'), data.get('dest_location'), data.get('contact_no')
    user_lat, user_lng = data.get('user_lat'), data.get('user_lng')
    
    if not all([source_location, dest_location, contact_no, user_lat, user_lng]):
        return jsonify({'error': 'Missing required fields (source_location, dest_location, contact_no, user_lat, user_lng)'}), 400

    assigned_driver = find_nearest_driver(source_location)
    if assigned_driver is None or "error" in assigned_driver:
        return jsonify({'success': False, 'message': assigned_driver.get('error', 'Could not find a driver.')}), 404
        
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO orders (contact_no, source_location, dest_location, driver_id) VALUES (%s, %s, %s, %s) RETURNING order_id;",
                    (contact_no, source_location, dest_location, assigned_driver['driver_id'])
                )
                order_id = cur.fetchone()[0]
                conn.commit()
            print(f'📝 Ride request stored in DB with Order ID: {order_id}')
            
            driver_start_coords = assigned_driver['coords']
            # Use the destination location's coordinates for the end point of the ride
            # This assumes the destination location is also in bangalore_locations
            dest_coords_data = bangalore_locations.get(dest_location)
            if not dest_coords_data:
                return jsonify({'success': False, 'message': 'Invalid destination location.'}), 400
            user_end_coords = dest_coords_data["coords"]
            
            active_rides[order_id] = {
                "driver_id": assigned_driver['driver_id'], "status": "in_transit",
                "waypoints": generate_waypoints(driver_start_coords, user_end_coords),
                "current_waypoint_idx": 0, "otp": None
            }
            return jsonify({
                'success': True, 'message': 'Driver assigned successfully!',
                'data': {
                    'order_id': order_id,
                    'driver_details': {
                        'driver_id': assigned_driver['driver_id'], 'name': assigned_driver['name'],
                        'car_model': assigned_driver['car_model'], 'location_name': assigned_driver['location_name'],
                        'vehicle_number': assigned_driver['vehicle_number'], 'phone_number': assigned_driver['phone_number'],
                        'initial_coords': driver_start_coords # Driver's initial location
                    },
                    'user_destination_coords': user_end_coords # User's destination coordinates
                }
            }), 201
        except Exception as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            return jsonify({'success': False, 'message': 'Failed to save ride to database', 'details': str(e)}), 500
        finally:
            conn.close()
    else:
        return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

@app.route('/api/server/drivers/location/<driver_id>', methods=['GET'])
def get_driver_location(driver_id):
    ride_data = next((v for k, v in active_rides.items() if v.get("driver_id") == driver_id and v.get("status") != "arrived"), None)
    if not ride_data: return jsonify({"error": "No active ride for this driver"}), 404

    driver = next((d for d in drivers if d["driver_id"] == driver_id), None)
    if not driver: return jsonify({"error": "Driver not found in system"}), 404

    current_waypoint_idx = ride_data["current_waypoint_idx"]
    
    # If driver has reached all waypoints, set status to arrived
    if current_waypoint_idx >= len(ride_data["waypoints"]):
        ride_data["status"] = "arrived"
        if not ride_data["otp"]: # Generate OTP only once
            ride_data["otp"] = generate_otp()
        return jsonify({"driver_id": driver_id, "status": "arrived", "otp": ride_data["otp"]})

    driver_lat, driver_lng = driver["coords"]
    target_lat, target_lng = ride_data["waypoints"][current_waypoint_idx]

    # Check if driver is close enough to the current waypoint to move to the next
    if haversine(driver_lat, driver_lng, target_lat, target_lng) < 50: # 50 meters threshold
        ride_data["current_waypoint_idx"] += 1
        # If moved to a new waypoint, update target
        if ride_data["current_waypoint_idx"] < len(ride_data["waypoints"]):
            target_lat, target_lng = ride_data["waypoints"][ride_data["current_waypoint_idx"]]
        else: # Driver has reached the final destination
            ride_data["status"] = "arrived"
            if not ride_data["otp"]:
                ride_data["otp"] = generate_otp()
            return jsonify({"driver_id": driver_id, "status": "arrived", "otp": ride_data["otp"]})

    # Move driver towards the current target waypoint
    # This simulates movement by moving 20% of the remaining distance
    new_lat = driver_lat + (target_lat - driver_lat) * 0.2
    new_lng = driver_lng + (target_lng - driver_lng) * 0.2
    driver["coords"] = (new_lat, new_lng) # Update driver's in-memory coordinates

    return jsonify({"driver_id": driver_id, "status": "in_transit", "latitude": new_lat, "longitude": new_lng})

if __name__ == '__main__':
    print('🛒 Main Amazon Server API starting...')
    print('📡 Listening on http://localhost:5002')
    app.run(host='0.0.0.0', port=5002, debug=True)