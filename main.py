import base64
import io
import json
import random
import sqlite3
import threading
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import qrcode
import webview

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "fare_settings.db"
USER_AGENT = "AreaFareDesktopStudentProject/1.0 (contact: local-user)"


def http_json(url, params=None, headers=None, timeout=25):
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    req = Request(url, headers=request_headers)
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


VEHICLE_RATES = {
    "Bus": 2.22,
    "Van": 2.0,
    "Taxi": 13.50,
    "Motor": 7.0,
    "Airplane": 50.0,
    "Ferry": 20.0,
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                base_fare REAL NOT NULL,
                base_distance REAL NOT NULL,
                rate_per_km REAL NOT NULL
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO settings (id, base_fare, base_distance, rate_per_km) VALUES (1, 15, 4, 2)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE NOT NULL,
                passenger_name TEXT NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                travel_date TEXT NOT NULL,
                travel_time TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                seat_number TEXT,
                distance_km REAL NOT NULL,
                fare REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


class FareAPI:
    def get_vehicle_rates(self):
        return {"ok": True, "rates": VEHICLE_RATES}

    def get_settings(self):
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT base_fare, base_distance, rate_per_km FROM settings WHERE id=1"
            ).fetchone()
        return {
            "base_fare": row[0],
            "base_distance": row[1],
            "rate_per_km": row[2],
        }

    def save_settings(self, base_fare, base_distance, rate_per_km):
        try:
            values = [float(base_fare), float(base_distance), float(rate_per_km)]
            if any(v < 0 for v in values):
                return {"ok": False, "error": "Fare settings cannot be negative."}
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE settings SET base_fare=?, base_distance=?, rate_per_km=? WHERE id=1",
                    values,
                )
            return {"ok": True, "settings": self.get_settings()}
        except (ValueError, TypeError):
            return {"ok": False, "error": "Enter valid numbers for all fare settings."}

    def search_address(self, query):
        query = str(query).strip()
        if len(query) < 3:
            return {"ok": False, "error": "Type at least 3 characters for an address."}
        try:
            # Nominatim asks clients to stay at or below one request per second.
            time.sleep(1.05)
            results = http_json(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "jsonv2", "limit": 10, "addressdetails": 1, "countrycodes": "ph"},
                timeout=25,
            )
            return {
                "ok": True,
                "results": [
                    {
                        "name": item.get("display_name", query),
                        "lat": float(item["lat"]),
                        "lon": float(item["lon"]),
                    }
                    for item in results
                ],
            }
        except Exception as exc:
            return {"ok": False, "error": f"Address search failed: {exc}"}

    def calculate_route(self, start_lat, start_lon, end_lat, end_lon, vehicle="Bus", passengers=1):
        try:
            coords = f"{float(start_lon)},{float(start_lat)};{float(end_lon)},{float(end_lat)}"
            data = http_json(
                f"https://router.project-osrm.org/route/v1/driving/{coords}",
                params={"overview": "full", "geometries": "geojson", "steps": "false"},
                timeout=35,
            )
            if data.get("code") != "Ok" or not data.get("routes"):
                return {"ok": False, "error": "No driving route was found between those points."}

            route = data["routes"][0]
            distance_km = route["distance"] / 1000.0
            vehicle_name = str(vehicle or "Bus").strip()
            rate_per_km = float(VEHICLE_RATES.get(vehicle_name, 2.22))
            try:
                passenger_count = max(1, int(passengers))
            except (ValueError, TypeError):
                passenger_count = 1

            fare_per_passenger = distance_km * rate_per_km
            total_fare = fare_per_passenger * passenger_count

            return {
                "ok": True,
                "distance_km": distance_km,
                "duration_minutes": route["duration"] / 60.0,
                "geometry": route["geometry"],
                "vehicle": vehicle_name,
                "rate_per_km": rate_per_km,
                "passengers": passenger_count,
                "fare_per_passenger": fare_per_passenger,
                "total_fare": total_fare,
            }
        except Exception as exc:
            return {"ok": False, "error": f"Route calculation failed: {exc}"}

    def generate_ticket(self, data):
        try:
            passenger_name = str(data.get("passenger_name", "")).strip() or "Passenger"
            origin = str(data.get("origin", "")).strip() or "Pickup Location"
            destination = str(data.get("destination", "")).strip() or "Destination"
            vehicle = str(data.get("vehicle", "Bus")).strip() or "Bus"
            seat_number = str(data.get("seat_number", "")).strip() or "RIDE"
            travel_date = str(data.get("travel_date", "")).strip() or time.strftime("%Y-%m-%d")
            travel_time = str(data.get("travel_time", "")).strip() or time.strftime("%H:%M")
            distance_km = float(data.get("distance_km", 0.0))
            fare = float(data.get("fare", 0.0))
            status = "CONFIRMED"

            ticket_number = f"TKT-{time.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

            # Encode verification payload into QR code
            qr_payload = (
                f"TICKET: {ticket_number}\n"
                f"PASSENGER: {passenger_name}\n"
                f"ORIGIN: {origin}\n"
                f"DESTINATION: {destination}\n"
                f"VEHICLE: {vehicle} | SEAT: {seat_number}\n"
                f"DATE: {travel_date} {travel_time}\n"
                f"DISTANCE: {distance_km:.2f} km\n"
                f"FARE: PHP {fare:.2f}\n"
                f"STATUS: {status}"
            )

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=3,
            )
            qr.add_data(qr_payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            qr_data_uri = f"data:image/png;base64,{qr_base64}"

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT INTO tickets (
                        ticket_number, passenger_name, origin, destination,
                        travel_date, travel_time, vehicle, seat_number,
                        distance_km, fare, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticket_number, passenger_name, origin, destination,
                        travel_date, travel_time, vehicle, seat_number,
                        distance_km, fare, status, now_str
                    ),
                )

            return {
                "ok": True,
                "ticket": {
                    "ticket_number": ticket_number,
                    "passenger_name": passenger_name,
                    "origin": origin,
                    "destination": destination,
                    "travel_date": travel_date,
                    "travel_time": travel_time,
                    "vehicle": vehicle,
                    "seat_number": seat_number,
                    "distance_km": distance_km,
                    "fare": fare,
                    "status": status,
                    "qr_data_uri": qr_data_uri,
                    "created_at": now_str,
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Failed to generate ticket: {exc}"}

    def get_recent_tickets(self, limit=10):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT ticket_number, passenger_name, origin, destination,
                           travel_date, travel_time, vehicle, seat_number,
                           distance_km, fare, status, created_at
                    FROM tickets
                    ORDER BY ticket_id DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                )
                rows = [dict(r) for r in cursor.fetchall()]
            return {"ok": True, "tickets": rows}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "tickets": []}


if __name__ == "__main__":
    init_db()
    api = FareAPI()
    window = webview.create_window(
        "Area-to-Area Fare Calculator",
        str(APP_DIR / "map.html"),
        js_api=api,
        width=1400,
        height=900,
        min_size=(1050, 700),
        background_color="#f5f7fb",
    )
    webview.start(debug=False)
