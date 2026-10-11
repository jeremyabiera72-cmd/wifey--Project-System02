from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    Response
)
import sqlite3
import hashlib
import io
import base64
import json
import qrcode

app = Flask(__name__)
app.secret_key = "travel_reservation_secret_key"

DATABASE = "travel_reservation.db"


VEHICLE_RATES = {
    "Bus": 12,
    "Van": 14,
    "Taxi": 18,
    "Motor": 10,
    "Airplane": 50,
    "Ferry": 20
}

VEHICLE_LIMITS = {
    "Bus": 45,
    "Van": 12,
    "Taxi": 4,
    "Motor": 1,
    "Airplane": 180,
    "Ferry": 57
}

VEHICLE_CAPACITY = {
    "Bus": 45,
    "Van": 12,
    "Taxi": 4,
    "Motor": 1,
    "Airplane": 180,
    "Ferry": 57
}

LAND_LOCATIONS = ["Molave","Pagadian City","Ipil","Zamboanga City","Dipolog City","Dapitan City","Iligan City","Ozamiz City","Cagayan de Oro City","Malaybalay City","Valencia City","Gingoog City","Butuan City","Surigao City","Davao City","Tagum City","Panabo City","Digos City","Mati City","General Santos City","Koronadal City","Kidapawan City","Tacurong City","Cotabato City"]
AIRPORT_LOCATIONS = ["Zamboanga International Airport","Pagadian Airport","Dipolog Airport","Laguindingan Airport","Labo Airport (Ozamiz)","Francisco Bangoy International Airport","General Santos International Airport","Cotabato Airport","Butuan Airport","Surigao Airport","Siargao Airport","Tandag Airport"]
PORT_LOCATIONS = ["Port of Zamboanga","Port of Iligan","Port of Cagayan de Oro","Port of Ozamiz","Port of Davao","Port of General Santos","Port of Surigao","Port of Dapitan","Port of Nasipit"]
VEHICLE_LOCATION_TYPES = {"Bus":"land","Van":"land","Taxi":"land","Motor":"land","Airplane":"air","Ferry":"sea"}
BARANGAYS_BY_CITY = {'Digos City': ['Digos City Proper', 'Aplaya', 'Balabag', 'Badiang', 'Binaton', 'Cogon', 'Colorado', 'Dawis', 'Kapatagan', 'Kiagot', 'Mahayahay', 'Matti', 'Rizal', 'San Jose', 'San Miguel', 'Sinawilan', 'Soong', 'Tiguman'], 'Davao City': ['Davao City Proper', 'Buhangin', 'Calinan', 'Toril', 'Tugbok', 'Paquibato', 'Baguio', 'Agdao', 'Bajada', 'Matina', 'Talomo'], 'Iligan City': ['Iligan City Proper', 'Acmac', 'Bagong Silang', 'Buru-un', 'Dalipuga', 'Hinaplanon', 'Kiwalan', 'Luinab', 'Pala-o', 'Poblacion', 'Tibanga', 'Tipanoy'], 'Cagayan de Oro City': ['Cagayan de Oro City Proper', 'Agusan', 'Balulang', 'Bugo', 'Bulua', 'Carmen', 'Gusa', 'Iponan', 'Lapasan', 'Lumbia', 'Macasandig', 'Puerto', 'Tignapoloan'], 'General Santos City': ['General Santos City Proper', 'Apopong', 'Bula', 'Calumpang', 'Conel', 'Fatima', 'Labangal', 'Lagao', 'San Isidro', 'Tambler'], 'Butuan City': ['Butuan City Proper', 'Ampayon', 'Baan', 'Bancasi', 'Buhang', 'Doongan', 'Dumalagan', 'Langihan', 'Libertad', 'Obrero'], 'Surigao City': ['Surigao City Proper', 'Anomar', 'Catadman', 'Ipil', 'Luna', 'Mat-i', 'San Isidro', 'Washington'], 'Cotabato City': ['Cotabato City Proper', 'Bagua', 'Kalanganan', 'Kalanganan II', 'Kamagayan', 'Mother Bagua', 'Rosary Heights', 'Tamontaka'], 'Zamboanga City': ['Zamboanga City Proper', 'Ayala', 'Baliwasan', 'Canelar', 'Guiwan', 'Mercedes', 'Putik', 'Recodo', 'San Roque', 'Tetuan'], 'Ozamiz City': ['Ozamiz City Proper', 'Aguada', 'Bongbong', 'Capucao', 'Catadman', 'Maningcol', 'Malaubang', 'Sinuza'], 'Dipolog City': ['Dipolog City Proper', 'Barra', 'Biasong', 'Central', 'Cogon', 'Galas', 'Miputak', 'Olingan'], 'Pagadian City': ['Pagadian City Proper', 'Balangasan', 'Bogo', 'Dao', 'Kawit', 'San Francisco', 'Tiguma'], 'Malaybalay City': ['Malaybalay City Proper', 'Aglayan', 'Bangcud', 'Cabangahan', 'Casisang', 'Kalasungay', 'Laguitas', 'San Jose'], 'Marawi City': ['Marawi City Proper', 'Banggolo', 'Boganga', 'Datu Saber', 'Lumbaca Madaya', 'Sagonsongan', 'Tuca'], 'Tagum City': ['Tagum City Proper', 'Apokon', 'Bincungan', 'Canocotan', 'Cuambogan', 'La Filipina', 'Magugpo', 'Mankilam', 'Visayan Village'], 'Molave': ['Molave Proper'], 'Ipil': ['Ipil Proper'], 'Dapitan City': ['Dapitan City Proper'], 'Valencia City': ['Valencia City Proper'], 'Gingoog City': ['Gingoog City Proper'], 'Panabo City': ['Panabo City Proper'], 'Mati City': ['Mati City Proper'], 'Koronadal City': ['Koronadal City Proper'], 'Kidapawan City': ['Kidapawan City Proper'], 'Tacurong City': ['Tacurong City Proper']}

TERMINALS_BY_CITY = {'Molave': ['Molave Bus Terminal', 'Molave Van Terminal'], 'Pagadian City': ['Pagadian City Bus Terminal', 'Pagadian City Van Terminal'], 'Ipil': ['Ipil Bus Terminal', 'Ipil Van Terminal'], 'Zamboanga City': ['Zamboanga City Bus Terminal', 'Zamboanga City Van Terminal'], 'Dipolog City': ['Dipolog City Bus Terminal', 'Dipolog City Van Terminal'], 'Dapitan City': ['Dapitan City Bus Terminal', 'Dapitan City Van Terminal'], 'Iligan City': ['Iligan City Bus Terminal', 'Iligan City Van Terminal'], 'Ozamiz City': ['Ozamiz City Bus Terminal', 'Ozamiz City Van Terminal'], 'Cagayan de Oro City': ['Cagayan de Oro City Bus Terminal', 'Cagayan de Oro City Van Terminal'], 'Malaybalay City': ['Malaybalay City Bus Terminal', 'Malaybalay City Van Terminal'], 'Valencia City': ['Valencia City Bus Terminal', 'Valencia City Van Terminal'], 'Gingoog City': ['Gingoog City Bus Terminal', 'Gingoog City Van Terminal'], 'Butuan City': ['Butuan City Bus Terminal', 'Butuan City Van Terminal'], 'Surigao City': ['Surigao City Bus Terminal', 'Surigao City Van Terminal'], 'Davao City': ['Davao City Bus Terminal', 'Davao City Van Terminal'], 'Tagum City': ['Tagum City Bus Terminal', 'Tagum City Van Terminal'], 'Panabo City': ['Panabo City Bus Terminal', 'Panabo City Van Terminal'], 'Digos City': ['Digos City Bus Terminal', 'Digos City Van Terminal'], 'Mati City': ['Mati City Bus Terminal', 'Mati City Van Terminal'], 'General Santos City': ['General Santos City Bus Terminal', 'General Santos City Van Terminal'], 'Koronadal City': ['Koronadal City Bus Terminal', 'Koronadal City Van Terminal'], 'Kidapawan City': ['Kidapawan City Bus Terminal', 'Kidapawan City Van Terminal'], 'Tacurong City': ['Tacurong City Bus Terminal', 'Tacurong City Van Terminal'], 'Cotabato City': ['Cotabato City Bus Terminal', 'Cotabato City Van Terminal']}

LOCATION_COORDINATES = {'Molave': (7.858, 123.424), 'Pagadian City': (7.8257, 123.437), 'Ipil': (7.785, 122.586), 'Zamboanga City': (6.9214, 122.079), 'Dipolog City': (8.588, 123.34), 'Dapitan City': (8.654, 123.424), 'Iligan City': (8.228, 124.245), 'Ozamiz City': (8.148, 123.84), 'Cagayan de Oro City': (8.4542, 124.6319), 'Malaybalay City': (8.1575, 125.1278), 'Valencia City': (7.9064, 125.095), 'Gingoog City': (8.828, 125.102), 'Butuan City': (8.9475, 125.5406), 'Surigao City': (9.789, 125.495), 'Davao City': (7.0707, 125.6087), 'Tagum City': (7.4478, 125.8078), 'Panabo City': (7.3081, 125.684), 'Digos City': (6.7497, 125.3572), 'Mati City': (6.955, 126.216), 'General Santos City': (6.1164, 125.1716), 'Koronadal City': (6.5, 124.846), 'Kidapawan City': (7.008, 125.089), 'Tacurong City': (6.692, 124.676), 'Cotabato City': (7.2236, 124.246), 'Zamboanga International Airport': (6.9224, 122.0598), 'Pagadian Airport': (7.8297, 123.4615), 'Dipolog Airport': (8.601, 123.341), 'Laguindingan Airport': (8.6125, 124.4565), 'Labo Airport (Ozamiz)': (8.178, 123.842), 'Francisco Bangoy International Airport': (7.125, 125.645), 'General Santos International Airport': (6.058, 125.096), 'Cotabato Airport': (7.1656, 124.2097), 'Butuan Airport': (8.9515, 125.477), 'Surigao Airport': (9.756, 125.48), 'Siargao Airport': (9.8591, 126.014), 'Tandag Airport': (9.0725, 126.171), 'Port of Zamboanga': (6.905, 122.08), 'Port of Iligan': (8.228, 124.245), 'Port of Cagayan de Oro': (8.485, 124.659), 'Port of Ozamiz': (8.15, 123.842), 'Port of Davao': (7.073, 125.617), 'Port of General Santos': (6.111, 125.171), 'Port of Surigao': (9.784, 125.49), 'Port of Dapitan': (8.656, 123.425), 'Port of Nasipit': (8.969, 125.292), 'Digos City Proper': (6.7497, 125.3572), 'Aplaya': (6.7497, 125.3572), 'Balabag': (6.7497, 125.3572), 'Badiang': (6.7497, 125.3572), 'Binaton': (6.7497, 125.3572), 'Cogon': (6.7497, 125.3572), 'Colorado': (6.7497, 125.3572), 'Dawis': (6.7497, 125.3572), 'Kapatagan': (6.7497, 125.3572), 'Kiagot': (6.7497, 125.3572), 'Mahayahay': (6.7497, 125.3572), 'Matti': (6.7497, 125.3572), 'Rizal': (6.7497, 125.3572), 'San Jose': (6.7497, 125.3572), 'San Miguel': (6.7497, 125.3572), 'Sinawilan': (6.7497, 125.3572), 'Soong': (6.7497, 125.3572), 'Tiguman': (6.7497, 125.3572), 'Davao City Proper': (7.0707, 125.6087), 'Buhangin': (7.0707, 125.6087), 'Calinan': (7.0707, 125.6087), 'Toril': (7.0707, 125.6087), 'Tugbok': (7.0707, 125.6087), 'Paquibato': (7.0707, 125.6087), 'Baguio': (7.0707, 125.6087), 'Agdao': (7.0707, 125.6087), 'Bajada': (7.0707, 125.6087), 'Matina': (7.0707, 125.6087), 'Talomo': (7.0707, 125.6087), 'Iligan City Proper': (8.228, 124.245), 'Acmac': (8.228, 124.245), 'Bagong Silang': (8.228, 124.245), 'Buru-un': (8.228, 124.245), 'Dalipuga': (8.228, 124.245), 'Hinaplanon': (8.228, 124.245), 'Kiwalan': (8.228, 124.245), 'Luinab': (8.228, 124.245), 'Pala-o': (8.228, 124.245), 'Poblacion': (8.228, 124.245), 'Tibanga': (8.228, 124.245), 'Tipanoy': (8.228, 124.245), 'Cagayan de Oro City Proper': (8.4542, 124.6319), 'Agusan': (8.4542, 124.6319), 'Balulang': (8.4542, 124.6319), 'Bugo': (8.4542, 124.6319), 'Bulua': (8.4542, 124.6319), 'Carmen': (8.4542, 124.6319), 'Gusa': (8.4542, 124.6319), 'Iponan': (8.4542, 124.6319), 'Lapasan': (8.4542, 124.6319), 'Lumbia': (8.4542, 124.6319), 'Macasandig': (8.4542, 124.6319), 'Puerto': (8.4542, 124.6319), 'Tignapoloan': (8.4542, 124.6319), 'General Santos City Proper': (6.1164, 125.1716), 'Apopong': (6.1164, 125.1716), 'Bula': (6.1164, 125.1716), 'Calumpang': (6.1164, 125.1716), 'Conel': (6.1164, 125.1716), 'Fatima': (6.1164, 125.1716), 'Labangal': (6.1164, 125.1716), 'Lagao': (6.1164, 125.1716), 'San Isidro': (6.1164, 125.1716), 'Tambler': (6.1164, 125.1716), 'Butuan City Proper': (8.9475, 125.5406), 'Ampayon': (8.9475, 125.5406), 'Baan': (8.9475, 125.5406), 'Bancasi': (8.9475, 125.5406), 'Buhang': (8.9475, 125.5406), 'Doongan': (8.9475, 125.5406), 'Dumalagan': (8.9475, 125.5406), 'Langihan': (8.9475, 125.5406), 'Libertad': (8.9475, 125.5406), 'Obrero': (8.9475, 125.5406), 'Surigao City Proper': (9.789, 125.495), 'Anomar': (9.789, 125.495), 'Catadman': (9.789, 125.495), 'Luna': (9.789, 125.495), 'Mat-i': (9.789, 125.495), 'Washington': (9.789, 125.495), 'Cotabato City Proper': (7.2236, 124.246), 'Bagua': (7.2236, 124.246), 'Kalanganan': (7.2236, 124.246), 'Kalanganan II': (7.2236, 124.246), 'Kamagayan': (7.2236, 124.246), 'Mother Bagua': (7.2236, 124.246), 'Rosary Heights': (7.2236, 124.246), 'Tamontaka': (7.2236, 124.246), 'Zamboanga City Proper': (6.9214, 122.079), 'Ayala': (6.9214, 122.079), 'Baliwasan': (6.9214, 122.079), 'Canelar': (6.9214, 122.079), 'Guiwan': (6.9214, 122.079), 'Mercedes': (6.9214, 122.079), 'Putik': (6.9214, 122.079), 'Recodo': (6.9214, 122.079), 'San Roque': (6.9214, 122.079), 'Tetuan': (6.9214, 122.079), 'Ozamiz City Proper': (8.148, 123.84), 'Aguada': (8.148, 123.84), 'Bongbong': (8.148, 123.84), 'Capucao': (8.148, 123.84), 'Maningcol': (8.148, 123.84), 'Malaubang': (8.148, 123.84), 'Sinuza': (8.148, 123.84), 'Dipolog City Proper': (8.588, 123.34), 'Barra': (8.588, 123.34), 'Biasong': (8.588, 123.34), 'Central': (8.588, 123.34), 'Galas': (8.588, 123.34), 'Miputak': (8.588, 123.34), 'Olingan': (8.588, 123.34), 'Pagadian City Proper': (7.8257, 123.437), 'Balangasan': (7.8257, 123.437), 'Bogo': (7.8257, 123.437), 'Dao': (7.8257, 123.437), 'Kawit': (7.8257, 123.437), 'San Francisco': (7.8257, 123.437), 'Tiguma': (7.8257, 123.437), 'Malaybalay City Proper': (8.1575, 125.1278), 'Aglayan': (8.1575, 125.1278), 'Bangcud': (8.1575, 125.1278), 'Cabangahan': (8.1575, 125.1278), 'Casisang': (8.1575, 125.1278), 'Kalasungay': (8.1575, 125.1278), 'Laguitas': (8.1575, 125.1278), 'Tagum City Proper': (7.4478, 125.8078), 'Apokon': (7.4478, 125.8078), 'Bincungan': (7.4478, 125.8078), 'Canocotan': (7.4478, 125.8078), 'Cuambogan': (7.4478, 125.8078), 'La Filipina': (7.4478, 125.8078), 'Magugpo': (7.4478, 125.8078), 'Mankilam': (7.4478, 125.8078), 'Visayan Village': (7.4478, 125.8078), 'Molave Proper': (7.858, 123.424), 'Ipil Proper': (7.785, 122.586), 'Dapitan City Proper': (8.654, 123.424), 'Valencia City Proper': (7.9064, 125.095), 'Gingoog City Proper': (8.828, 125.102), 'Panabo City Proper': (7.3081, 125.684), 'Mati City Proper': (6.955, 126.216), 'Koronadal City Proper': (6.5, 124.846), 'Kidapawan City Proper': (7.008, 125.089), 'Tacurong City Proper': (6.692, 124.676), 'Molave Bus Terminal': (7.858, 123.424), 'Molave Van Terminal': (7.858, 123.424), 'Pagadian City Bus Terminal': (7.8257, 123.437), 'Pagadian City Van Terminal': (7.8257, 123.437), 'Ipil Bus Terminal': (7.785, 122.586), 'Ipil Van Terminal': (7.785, 122.586), 'Zamboanga City Bus Terminal': (6.9214, 122.079), 'Zamboanga City Van Terminal': (6.9214, 122.079), 'Dipolog City Bus Terminal': (8.588, 123.34), 'Dipolog City Van Terminal': (8.588, 123.34), 'Dapitan City Bus Terminal': (8.654, 123.424), 'Dapitan City Van Terminal': (8.654, 123.424), 'Iligan City Bus Terminal': (8.228, 124.245), 'Iligan City Van Terminal': (8.228, 124.245), 'Ozamiz City Bus Terminal': (8.148, 123.84), 'Ozamiz City Van Terminal': (8.148, 123.84), 'Cagayan de Oro City Bus Terminal': (8.4542, 124.6319), 'Cagayan de Oro City Van Terminal': (8.4542, 124.6319), 'Malaybalay City Bus Terminal': (8.1575, 125.1278), 'Malaybalay City Van Terminal': (8.1575, 125.1278), 'Valencia City Bus Terminal': (7.9064, 125.095), 'Valencia City Van Terminal': (7.9064, 125.095), 'Gingoog City Bus Terminal': (8.828, 125.102), 'Gingoog City Van Terminal': (8.828, 125.102), 'Butuan City Bus Terminal': (8.9475, 125.5406), 'Butuan City Van Terminal': (8.9475, 125.5406), 'Surigao City Bus Terminal': (9.789, 125.495), 'Surigao City Van Terminal': (9.789, 125.495), 'Davao City Bus Terminal': (7.0707, 125.6087), 'Davao City Van Terminal': (7.0707, 125.6087), 'Tagum City Bus Terminal': (7.4478, 125.8078), 'Tagum City Van Terminal': (7.4478, 125.8078), 'Panabo City Bus Terminal': (7.3081, 125.684), 'Panabo City Van Terminal': (7.3081, 125.684), 'Digos City Bus Terminal': (6.7497, 125.3572), 'Digos City Van Terminal': (6.7497, 125.3572), 'Mati City Bus Terminal': (6.955, 126.216), 'Mati City Van Terminal': (6.955, 126.216), 'General Santos City Bus Terminal': (6.1164, 125.1716), 'General Santos City Van Terminal': (6.1164, 125.1716), 'Koronadal City Bus Terminal': (6.5, 124.846), 'Koronadal City Van Terminal': (6.5, 124.846), 'Kidapawan City Bus Terminal': (7.008, 125.089), 'Kidapawan City Van Terminal': (7.008, 125.089), 'Tacurong City Bus Terminal': (6.692, 124.676), 'Tacurong City Van Terminal': (6.692, 124.676), 'Cotabato City Bus Terminal': (7.2236, 124.246), 'Cotabato City Van Terminal': (7.2236, 124.246)}

def calculate_distance_km(starting_location, destination):
    """Calculate approximate straight-line distance in kilometers."""
    a = LOCATION_COORDINATES.get(starting_location)
    b = LOCATION_COORDINATES.get(destination)
    if not a or not b:
        return None

    import math
    r = 6371.0088
    lat1 = math.radians(a[0])
    lat2 = math.radians(b[0])
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def add_missing_column(cursor, table_name, column_name, column_definition):
    """Safely add a column to an existing SQLite database."""
    columns = cursor.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = {row["name"] for row in columns}

    if column_name not in existing_columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN "
            f"{column_name} {column_definition}"
        )


def get_booking_type(vehicle):
    if vehicle in ("Bus", "Van"):
        return "Seat Reservation"
    if vehicle in ("Taxi", "Motor"):
        return "Ride Reservation"
    if vehicle in ("Airplane", "Ferry"):
        return "Ticket Reservation"
    return "Reservation"


def create_ticket_number(reservation_id, passenger_index):
    """
    Ticket number is unique per passenger.
    Example: TRS-000001-01
    """
    return f"TRS-{reservation_id:06d}-{passenger_index:02d}"


def get_seat_list(vehicle):
    """
    Generates realistic seat/slot labels.
    """
    if vehicle == "Bus":
        return [f"A{i}" for i in range(1, 46)]

    if vehicle == "Van":
        return [f"V{i}" for i in range(1, 13)]

    if vehicle == "Taxi":
        return [f"T{i}" for i in range(1, 5)]

    if vehicle == "Motor":
        return ["M1"]

    if vehicle == "Airplane":
        seats = []
        for row in range(1, 31):
            for letter in ["A", "B", "C", "D", "E", "F"]:
                seats.append(f"{row}{letter}")
        return seats

    if vehicle == "Ferry":
        return [f"B{i}" for i in range(1, 58)]

    return []


def get_trip_key(reservation):
    """
    A trip is considered the same when vehicle, date, time,
    origin, destination, and starting location are the same.
    """
    return (
        reservation["starting_location"],
        reservation["origin"],
        reservation["destination"],
        reservation["travel_date"],
        reservation["travel_time"],
        reservation["vehicle"]
    )


def assign_seats(conn, reservation, number_of_passengers):
    """
    Automatically assigns the first available seats for this trip.

    Cancelled tickets are ignored, so their seats become available again.
    """
    vehicle = reservation["vehicle"]
    available_seats = get_seat_list(vehicle)

    if len(available_seats) < number_of_passengers:
        raise ValueError(f"{vehicle} does not have enough available seats.")

    starting_location, origin, destination, travel_date, travel_time, vehicle = get_trip_key(
        reservation
    )

    used_rows = conn.execute(
        """
        SELECT seat_number
        FROM tickets
        WHERE starting_location = ?
          AND origin = ?
          AND destination = ?
          AND travel_date = ?
          AND travel_time = ?
          AND vehicle = ?
          AND status != 'Cancelled'
        ORDER BY ticket_id
        """,
        (
            starting_location,
            origin,
            destination,
            travel_date,
            travel_time,
            vehicle
        )
    ).fetchall()

    used_seats = {
        row["seat_number"]
        for row in used_rows
        if row["seat_number"]
    }

    selected = []

    for seat in available_seats:
        if seat not in used_seats:
            selected.append(seat)

        if len(selected) == number_of_passengers:
            break

    if len(selected) < number_of_passengers:
        raise ValueError(
            f"No more seats are available for {vehicle} on this trip."
        )

    return selected


def make_qr_data_uri(ticket_number):
    """
    Creates a QR image that contains the dynamic verification URL.
    The URL is generated from the current host used by the browser.
    """
    verification_url = url_for(
        "verify_ticket",
        ticket_number=ticket_number,
        _external=True
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    image = qr.make_image()
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")

    encoded = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return (
        f"data:image/png;base64,{encoded}",
        verification_url
    )


def create_tickets_for_reservation(conn, reservation_id):
    """
    Creates one ticket per passenger for a reservation.

    If tickets already exist, it does not create duplicates.
    """
    reservation = conn.execute(
        """
        SELECT *
        FROM reservations
        WHERE reservation_id = ?
        """,
        (reservation_id,)
    ).fetchone()

    if not reservation:
        raise ValueError("Reservation not found.")

    existing_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE reservation_id = ?
        """,
        (reservation_id,)
    ).fetchone()[0]

    if existing_count > 0:
        return

    number_of_passengers = int(reservation["passengers"])

    seats = assign_seats(
        conn,
        reservation,
        number_of_passengers
    )

    passenger_names = []

    saved_names = reservation["passenger_names"]

    if saved_names:
        try:
            passenger_names = json.loads(saved_names)
        except (TypeError, json.JSONDecodeError):
            passenger_names = []

    passenger_names = [
        str(name).strip()
        for name in passenger_names
        if str(name).strip()
    ]

    if len(passenger_names) != number_of_passengers:
        passenger_names = [
            reservation["passenger_name"]
            for _ in range(number_of_passengers)
        ]

    for index in range(number_of_passengers):
        ticket_number = create_ticket_number(
            reservation_id,
            index + 1
        )

        conn.execute(
            """
            INSERT INTO tickets (
                reservation_id,
                user_id,
                passenger_name,
                contact,
                starting_location,
                origin,
                destination,
                travel_date,
                travel_time,
                vehicle,
                seat_number,
                fare,
                status,
                booking_type,
                passengers,
                ticket_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reservation["reservation_id"],
                reservation["user_id"],
                passenger_names[index],
                reservation["contact"],
                reservation["starting_location"],
                reservation["origin"],
                reservation["destination"],
                reservation["travel_date"],
                reservation["travel_time"],
                reservation["vehicle"],
                seats[index],
                reservation["fare"],
                reservation["status"],
                get_booking_type(reservation["vehicle"]),
                number_of_passengers,
                ticket_number
            )
        )


def ensure_tickets_for_old_reservations():
    """
    Gives older reservations tickets after the new system is installed.
    """
    conn = get_db()

    reservations = conn.execute(
        """
        SELECT reservation_id
        FROM reservations
        ORDER BY reservation_id
        """
    ).fetchall()

    for row in reservations:
        try:
            create_tickets_for_reservation(
                conn,
                row["reservation_id"]
            )
        except ValueError:
            pass

    conn.commit()
    conn.close()


def init_database():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            contact TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            passenger_names TEXT,
            contact TEXT NOT NULL,
            starting_location TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            travel_time TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            distance REAL DEFAULT 0,
            fare REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    add_missing_column(
        cursor,
        "reservations",
        "passenger_names",
        "TEXT"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            starting_location TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            travel_time TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            seat_number TEXT NOT NULL,
            fare REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            booking_type TEXT,
            passengers INTEGER DEFAULT 1,
            ticket_number TEXT UNIQUE NOT NULL,
            FOREIGN KEY (reservation_id)
                REFERENCES reservations(reservation_id),
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
        )
        """
    )

    add_missing_column(
        cursor,
        "tickets",
        "ticket_number",
        "TEXT"
    )

    add_missing_column(
        cursor,
        "tickets",
        "seat_number",
        "TEXT"
    )

    add_missing_column(
        cursor,
        "tickets",
        "booking_type",
        "TEXT"
    )

    add_missing_column(
        cursor,
        "tickets",
        "passengers",
        "INTEGER DEFAULT 1"
    )

    cursor.execute(
        """
        UPDATE tickets
        SET booking_type = CASE
            WHEN vehicle IN ('Bus', 'Van')
                THEN 'Seat Reservation'
            WHEN vehicle IN ('Taxi', 'Motor')
                THEN 'Ride Reservation'
            WHEN vehicle IN ('Airplane', 'Ferry')
                THEN 'Ticket Reservation'
            ELSE 'Reservation'
        END
        WHERE booking_type IS NULL OR booking_type = ''
        """
    )

    admin_password = hash_password("admin123")

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (full_name, username, password, contact)
        VALUES (?, ?, ?, ?)
        """,
        (
            "System Administrator",
            "admin",
            admin_password,
            "Admin"
        )
    )

    conn.commit()
    conn.close()

    ensure_tickets_for_old_reservations()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = hash_password(request.form["password"])

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
              AND password = ?
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]

            if username == "admin":
                session["is_admin"] = True
                return redirect(url_for("admin_dashboard"))

            session["is_admin"] = False
            return redirect(url_for("dashboard"))

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        username = request.form["username"].strip()
        contact = request.form["contact"].strip()

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "error"
            )
            return redirect(url_for("register"))

        if len(password) < 6:
            flash(
                "Password must be at least 6 characters.",
                "error"
            )
            return redirect(url_for("register"))

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (full_name, username, password, contact)
                VALUES (?, ?, ?, ?)
                """,
                (
                    full_name,
                    username,
                    hash_password(password),
                    contact
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(url_for("register"))

        conn.close()

        flash(
            "Registration successful. You can now login.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["user_id"] = 0
            session["username"] = "admin"
            session["full_name"] = "System Administrator"
            session["is_admin"] = True

            return redirect(url_for("admin_dashboard"))

        flash(
            "Invalid admin username or password.",
            "error"
        )

    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") == "admin":
        return redirect(url_for("admin_dashboard"))

    conn = get_db()

    reservations = conn.execute(
        """
        SELECT *
        FROM reservations
        WHERE user_id = ?
        ORDER BY reservation_id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    tickets = conn.execute(
        """
        SELECT *
        FROM tickets
        WHERE user_id = ?
        ORDER BY ticket_id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        full_name=session["full_name"],
        reservations=reservations,
        tickets=tickets
    )

@app.route("/reservation", methods=["GET", "POST"])
def reservation():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") == "admin":
        flash(
            "Please use the customer account for reservations.",
            "error"
        )
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        try:
            passenger_names = [
                name.strip()
                for name in request.form.getlist("passenger_names[]")
                if name.strip()
            ]

            if not passenger_names:
                old_name = request.form.get(
                    "passenger_name",
                    ""
                ).strip()

                if old_name:
                    passenger_names = [old_name]

            contact = request.form["contact"].strip()

            starting_location = request.form[
                "starting_location"
            ].strip()

            origin = request.form.get("origin", "").strip()
            destination = request.form["destination"].strip()

            travel_date = request.form["travel_date"]
            travel_time = request.form["travel_time"]

            vehicle = request.form["vehicle"]

            passengers = int(
                request.form["passengers"]
            )

            distance_value = request.form.get("distance", "").strip()
            distance = float(distance_value) if distance_value else 0.0

        except (KeyError, ValueError):
            flash(
                "Please complete all reservation fields correctly.",
                "error"
            )
            return redirect(url_for("reservation"))

        if not passenger_names:
            flash(
                "Please enter at least one passenger name.",
                "error"
            )
            return redirect(url_for("reservation"))

        if len(passenger_names) != passengers:
            flash(
                "The number of passenger names must match "
                "the number of passengers.",
                "error"
            )
            return redirect(url_for("reservation"))

        passenger_name = passenger_names[0]

        if not contact:
            flash(
                "Contact number is required.",
                "error"
            )
            return redirect(url_for("reservation"))

        if vehicle not in VEHICLE_RATES:
            flash(
                "Invalid vehicle selected.",
                "error"
            )
            return redirect(url_for("reservation"))

        location_type = VEHICLE_LOCATION_TYPES.get(vehicle)

        if not starting_location or not destination:
            flash(
                "Please complete the location fields.",
                "error"
            )
            return redirect(url_for("reservation"))

        if location_type == "land" and not origin:
            flash(
                "Please select an origin municipality/city.",
                "error"
            )
            return redirect(url_for("reservation"))

        if distance <= 0:
            calculated_distance = calculate_distance_km(
                starting_location,
                destination
            )
            if calculated_distance is not None:
                distance = round(calculated_distance, 1)

        if distance <= 0:
            flash(
                "Distance could not be calculated for the selected locations.",
                "error"
            )
            return redirect(url_for("reservation"))

        if vehicle not in VEHICLE_RATES:
            flash(
                "Invalid vehicle selected.",
                "error"
            )
            return redirect(url_for("reservation"))

        if passengers < 1:
            flash(
                "Passenger count must be at least 1.",
                "error"
            )
            return redirect(url_for("reservation"))

        if passengers > VEHICLE_LIMITS[vehicle]:
            flash(
                f"{vehicle} can only accommodate "
                f"{VEHICLE_LIMITS[vehicle]} passenger(s) "
                f"per booking.",
                "error"
            )
            return redirect(url_for("reservation"))

        if distance <= 0:
            flash(
                "Distance must be greater than 0.",
                "error"
            )
            return redirect(url_for("reservation"))

        fare = distance * VEHICLE_RATES[vehicle]

        conn = get_db()

        try:
            conn.execute("BEGIN IMMEDIATE")

            cursor = conn.execute(
                """
                INSERT INTO reservations (
                    user_id,
                    passenger_name,
                    passenger_names,
                    contact,
                    starting_location,
                    origin,
                    destination,
                    travel_date,
                    travel_time,
                    vehicle,
                    passengers,
                    distance,
                    fare,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    passenger_name,
                    json.dumps(
                        passenger_names,
                        ensure_ascii=False
                    ),
                    contact,
                    starting_location,
                    origin,
                    destination,
                    travel_date,
                    travel_time,
                    vehicle,
                    passengers,
                    distance,
                    fare,
                    "Pending"
                )
            )

            reservation_id = cursor.lastrowid

            reservation_row = conn.execute(
                """
                SELECT *
                FROM reservations
                WHERE reservation_id = ?
                """,
                (reservation_id,)
            ).fetchone()

            assign_seats(
                conn,
                reservation_row,
                passengers
            )

            create_tickets_for_reservation(
                conn,
                reservation_id
            )

            conn.commit()

        except ValueError as error:
            conn.rollback()
            conn.close()

            flash(
                str(error),
                "error"
            )
            return redirect(url_for("reservation"))

        except sqlite3.Error as error:
            conn.rollback()
            conn.close()

            flash(
                f"Reservation could not be saved: {error}",
                "error"
            )
            return redirect(url_for("reservation"))

        conn.close()

        flash(
            f"Reservation submitted successfully! "
            f"{passengers} individual ticket(s) were created "
            f"with automatic seat assignment.",
            "success"
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "reservation.html",
        vehicle_rates=VEHICLE_RATES,
        vehicle_limits=VEHICLE_LIMITS,
        vehicle_capacity=VEHICLE_CAPACITY,
        land_locations=LAND_LOCATIONS,
        airport_locations=AIRPORT_LOCATIONS,
        port_locations=PORT_LOCATIONS,
        vehicle_location_types=VEHICLE_LOCATION_TYPES,
        location_coordinates=LOCATION_COORDINATES,
        barangays_by_city=BARANGAYS_BY_CITY,
        terminals_by_city=TERMINALS_BY_CITY
    )


@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") != "admin":
        flash(
            "Admin access only.",
            "error"
        )
        return redirect(url_for("dashboard"))

    conn = get_db()

    reservations = conn.execute(
        """
        SELECT
            r.*,
            u.full_name AS account_name,
            u.username,
            (
                SELECT t.ticket_number
                FROM tickets t
                WHERE t.reservation_id = r.reservation_id
                ORDER BY t.ticket_id
                LIMIT 1
            ) AS first_ticket_number
        FROM reservations r
        JOIN users u
            ON r.user_id = u.user_id
        ORDER BY r.reservation_id DESC
        """
    ).fetchall()

    tickets = conn.execute(
        """
        SELECT
            t.*,
            u.full_name AS account_name,
            u.username
        FROM tickets t
        JOIN users u
            ON t.user_id = u.user_id
        ORDER BY t.ticket_id DESC
        """
    ).fetchall()

    users = conn.execute(
        """
        SELECT
            user_id,
            full_name,
            username,
            contact
        FROM users
        ORDER BY user_id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        reservations=reservations,
        tickets=tickets,
        users=users
    )

@app.route(
    "/admin/update-status/<int:reservation_id>",
    methods=["POST"]
)
def update_status(reservation_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") != "admin":
        flash(
            "Admin access only.",
            "error"
        )
        return redirect(url_for("dashboard"))

    new_status = request.form.get("status")

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Cancelled",
        "Completed"
    ]

    if new_status not in allowed_statuses:
        flash(
            "Invalid reservation status.",
            "error"
        )
        return redirect(
            url_for("admin_dashboard")
        )

    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            """
            UPDATE reservations
            SET status = ?
            WHERE reservation_id = ?
            """,
            (
                new_status,
                reservation_id
            )
        )

        conn.execute(
            """
            UPDATE tickets
            SET status = ?
            WHERE reservation_id = ?
            """,
            (
                new_status,
                reservation_id
            )
        )

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        conn.close()

        flash(
            f"Status update failed: {error}",
            "error"
        )
        return redirect(
            url_for("admin_dashboard")
        )

    conn.close()

    flash(
        f"Reservation #{reservation_id} status updated to "
        f"{new_status}.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )

@app.route("/reservation/edit/<int:reservation_id>", methods=["GET", "POST"])
def edit_reservation(reservation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") == "admin":
        flash("Please manage reservations from the admin dashboard.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    reservation_row = conn.execute(
        """
        SELECT * FROM reservations
        WHERE reservation_id = ? AND user_id = ?
        """,
        (reservation_id, session["user_id"])
    ).fetchone()
    conn.close()

    if not reservation_row:
        abort(404)

    if reservation_row["status"] in ("Cancelled", "Completed"):
        flash("This reservation can no longer be edited.", "error")
        return redirect(url_for("dashboard"))

    saved_names = []
    if reservation_row["passenger_names"]:
        try:
            saved_names = json.loads(reservation_row["passenger_names"])
        except (TypeError, json.JSONDecodeError):
            saved_names = []

    if not saved_names:
        saved_names = [reservation_row["passenger_name"]] * int(reservation_row["passengers"])

    if request.method == "POST":
        try:
            passenger_names = [
                name.strip()
                for name in request.form.getlist("passenger_names[]")
                if name.strip()
            ]
            contact = request.form["contact"].strip()
            starting_location = request.form["starting_location"].strip()
            origin = request.form["origin"].strip()
            destination = request.form["destination"].strip()
            travel_date = request.form["travel_date"]
            travel_time = request.form["travel_time"]
            vehicle = request.form["vehicle"]
            passengers = int(request.form["passengers"])
            distance = float(request.form["distance"])
        except (KeyError, ValueError):
            flash("Please complete all reservation fields correctly.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        if not passenger_names or len(passenger_names) != passengers:
            flash("The number of passenger names must match the number of passengers.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        if not contact or not starting_location or not origin or not destination:
            flash("Please complete all required fields.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        if vehicle not in VEHICLE_RATES:
            flash("Invalid vehicle selected.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        if passengers < 1 or passengers > VEHICLE_LIMITS[vehicle]:
            flash(f"{vehicle} can only accommodate {VEHICLE_LIMITS[vehicle]} passenger(s) per booking.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        if distance <= 0:
            flash("Distance must be greater than 0.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        fare = distance * VEHICLE_RATES[vehicle]
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")

            conn.execute(
                "DELETE FROM tickets WHERE reservation_id = ?",
                (reservation_id,)
            )

            conn.execute(
                """
                UPDATE reservations
                SET passenger_name = ?, passenger_names = ?, contact = ?,
                    starting_location = ?, origin = ?, destination = ?,
                    travel_date = ?, travel_time = ?, vehicle = ?,
                    passengers = ?, distance = ?, fare = ?, status = 'Pending'
                WHERE reservation_id = ? AND user_id = ?
                """,
                (
                    passenger_names[0],
                    json.dumps(passenger_names, ensure_ascii=False),
                    contact,
                    starting_location,
                    origin,
                    destination,
                    travel_date,
                    travel_time,
                    vehicle,
                    passengers,
                    distance,
                    fare,
                    reservation_id,
                    session["user_id"]
                )
            )

            updated = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id = ?",
                (reservation_id,)
            ).fetchone()

            assign_seats(conn, updated, passengers)
            create_tickets_for_reservation(conn, reservation_id)
            conn.commit()

        except (ValueError, sqlite3.Error) as error:
            conn.rollback()
            conn.close()
            flash(f"Reservation update failed: {error}", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        conn.close()
        flash("Reservation updated successfully. New seats and tickets were assigned.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "edit_reservation.html",
        reservation=reservation_row,
        passenger_names=saved_names,
        vehicle_rates=VEHICLE_RATES,
        vehicle_limits=VEHICLE_LIMITS,
        vehicle_capacity=VEHICLE_CAPACITY
    )

@app.route("/reservation/cancel/<int:reservation_id>", methods=["POST"])
def cancel_reservation(reservation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") == "admin":
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT status FROM reservations
            WHERE reservation_id = ? AND user_id = ?
            """,
            (reservation_id, session["user_id"])
        ).fetchone()

        if not row:
            conn.rollback()
            conn.close()
            abort(404)

        if row["status"] in ("Cancelled", "Completed"):
            conn.rollback()
            conn.close()
            flash("This reservation cannot be cancelled.", "error")
            return redirect(url_for("dashboard"))

        conn.execute(
            "UPDATE reservations SET status = 'Cancelled' WHERE reservation_id = ? AND user_id = ?",
            (reservation_id, session["user_id"])
        )
        conn.execute(
            "UPDATE tickets SET status = 'Cancelled' WHERE reservation_id = ? AND user_id = ?",
            (reservation_id, session["user_id"])
        )
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        conn.close()
        flash(f"Cancellation failed: {error}", "error")
        return redirect(url_for("dashboard"))

    conn.close()
    flash("Reservation cancelled successfully. The admin dashboard is updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/reservation/delete/<int:reservation_id>", methods=["POST"])
def delete_reservation(reservation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") == "admin":
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT status FROM reservations
            WHERE reservation_id = ? AND user_id = ?
            """,
            (reservation_id, session["user_id"])
        ).fetchone()

        if not row:
            conn.rollback()
            conn.close()
            abort(404)

        if row["status"] not in ("Cancelled", "Pending"):
            conn.rollback()
            conn.close()
            flash("Only Pending or Cancelled reservations can be deleted.", "error")
            return redirect(url_for("dashboard"))

        conn.execute("DELETE FROM tickets WHERE reservation_id = ?", (reservation_id,))
        conn.execute(
            "DELETE FROM reservations WHERE reservation_id = ? AND user_id = ?",
            (reservation_id, session["user_id"])
        )
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        conn.close()
        flash(f"Delete failed: {error}", "error")
        return redirect(url_for("dashboard"))

    conn.close()
    flash("Reservation deleted successfully. It is also removed from the admin dashboard.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/delete-reservation/<int:reservation_id>", methods=["POST"])
def admin_delete_reservation(reservation_id):
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT reservation_id FROM reservations WHERE reservation_id = ?",
            (reservation_id,)
        ).fetchone()
        if not row:
            conn.rollback()
            conn.close()
            abort(404)

        conn.execute("DELETE FROM tickets WHERE reservation_id = ?", (reservation_id,))
        conn.execute("DELETE FROM reservations WHERE reservation_id = ?", (reservation_id,))
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        conn.close()
        flash(f"Admin delete failed: {error}", "error")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    flash(f"Reservation #{reservation_id} deleted successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/ticket/<ticket_number>")
def view_ticket(ticket_number):

    conn = get_db()

    ticket = conn.execute(
        """
        SELECT *
        FROM tickets
        WHERE ticket_number = ?
        """,
        (ticket_number,)
    ).fetchone()

    conn.close()

    if not ticket:
        abort(404)

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") != "admin":
        if ticket["user_id"] != session.get("user_id"):
            flash(
                "You can only view your own ticket.",
                "error"
            )
            return redirect(url_for("dashboard"))

    qr_data_uri, verification_url = make_qr_data_uri(
        ticket["ticket_number"]
    )

    return render_template(
        "ticket.html",
        ticket=ticket,
        qr_data_uri=qr_data_uri,
        verification_url=verification_url
    )

@app.route("/receipt/<ticket_number>")
def view_receipt(ticket_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    ticket = conn.execute(
        """
        SELECT
            t.*,
            r.distance AS distance,
            u.full_name AS account_name,
            u.username
        FROM tickets t
        JOIN reservations r
            ON t.reservation_id = r.reservation_id
        JOIN users u
            ON t.user_id = u.user_id
        WHERE t.ticket_number = ?
        """,
        (ticket_number,)
    ).fetchone()

    conn.close()

    if not ticket:
        abort(404)

    if session.get("username") != "admin":
        if ticket["user_id"] != session.get("user_id"):
            flash(
                "You can only view your own receipt.",
                "error"
            )
            return redirect(url_for("dashboard"))

    return render_template(
        "receipt.html",
        ticket=ticket
    )

@app.route("/ticket/<ticket_number>/qr.png")
def ticket_qr_png(ticket_number):

    conn = get_db()

    ticket = conn.execute(
        """
        SELECT ticket_number
        FROM tickets
        WHERE ticket_number = ?
        """,
        (ticket_number,)
    ).fetchone()

    conn.close()

    if not ticket:
        abort(404)

    verification_url = url_for(
        "verify_ticket",
        ticket_number=ticket_number,
        _external=True
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    image = qr.make_image()

    image_buffer = io.BytesIO()
    image.save(
        image_buffer,
        format="PNG"
    )

    image_buffer.seek(0)

    response = Response(
        image_buffer.getvalue(),
        mimetype="image/png"
    )

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )

    return response


@app.route("/verify/<ticket_number>")
def verify_ticket(ticket_number):

    conn = get_db()

    ticket = conn.execute(
        """
        SELECT
            ticket_id,
            ticket_number,
            reservation_id,
            passenger_name,
            contact,
            starting_location,
            origin,
            destination,
            travel_date,
            travel_time,
            vehicle,
            seat_number,
            fare,
            status
        FROM tickets
        WHERE ticket_number = ?
        """,
        (ticket_number,)
    ).fetchone()

    conn.close()

    response = make_response_with_no_cache(
        render_template(
            "verify.html",
            ticket=ticket
        )
    )

    return response


def make_response_with_no_cache(content):
    response = Response(
        content,
        mimetype="text/html"
    )

    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


if __name__ == "__main__":

    init_database()

    print("")
    print("==============================================")
    print("  WEB-BASED TRAVEL RESERVATION SYSTEM")
    print("==============================================")
    print("Local:   http://127.0.0.1:5000")
    print("Network: http://<YOUR-LAPTOP-IP>:5000")
    print("Admin:   username=admin | password=admin123")
    print("==============================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
