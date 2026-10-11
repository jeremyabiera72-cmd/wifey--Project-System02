# Area-to-Area Fare Calculator (Python Desktop)

A desktop fare estimator with:
- Admin-configurable base fare, included distance, and succeeding-kilometer rate
- Address search using OpenStreetMap Nominatim
- Map-click pickup and destination pins
- Driving-route distance and route geometry from OSRM
- SQLite storage for fare settings and issued tickets
- Printable Travel Ticket & Boarding Pass with dynamic verification QR codes

## Requirements

- Python 3.10+
- Internet connection
- A desktop environment capable of running pywebview (Linux may need a WebKitGTK package)

## Install

Create and activate a virtual environment (recommended), then run:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Then run `python main.py`.

## Linux notes

`pywebview` needs a supported webview backend. On many Ubuntu/Debian systems, install WebKitGTK system dependencies if the app reports that no GUI backend is available. On Arch Linux, install the relevant GTK/WebKitGTK packages using your package manager, then install the Python requirements.

## How to use

1. Edit the admin fare values and click **Save fare settings**.
2. Search a pickup address and destination, or click **Set next map click as pickup/destination** and place pins.
3. Click **Calculate road distance & fare**.
4. Read the route distance, extra distance, extra charge, total fare, and average fare per kilometer.

Default settings are ₱15 base fare, 4 km included, and ₱2 per succeeding kilometer. Settings are stored in `fare_settings.db` next to `main.py`.

## Fare formula

`total_fare = base_fare + max(0, road_distance_km - base_distance_km) * rate_per_km`

## Important service notes

- Address search uses the public Nominatim service. Its public policy requires a descriptive User-Agent and a maximum rate of one request per second. Use it respectfully; for a production app with multiple users, choose a provider or host your own geocoder.
- Routing uses the public OSRM demo server, which is intended for demonstration and has no production availability guarantee. Use a suitable hosted or self-hosted routing service before relying on this for a real transportation business.
- Map tiles are provided by OpenStreetMap contributors and require internet access. Follow the tile usage policy.
- This is a fare estimator, not a guaranteed quote. Confirm the applicable local fare rules before using it for actual passenger charges.
