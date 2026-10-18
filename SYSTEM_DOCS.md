# Travel Reservation System — Documentation

A web-based booking and ticketing system for a small transport operator. Customers
register, pick a vehicle type, enter a pickup and destination, and get a
distance-based fare estimate. On confirmation the system stores the quoted fare,
assigns seats, and issues printable tickets with QR verification. Admins manage
vehicle types, their pricing rules, the individual vehicles, and every booking.

Everything runs on Flask + SQLite. No build step, no ORM, no JS framework.

---

## 1. What lives in this repository

The repo contains **two independent programs** that share the same idea:

| Path | What it is |
|---|---|
| `TravelReservationSystem/` | **The main system.** Multi-user Flask web app: registration, login, reservations, tickets, admin dashboard, fare configuration. This is what this document describes. |
| `main.py`, `map.html`, `ticket.html`, `fare_settings.db` | An earlier **pywebview desktop prototype** ("Area-to-Area Fare Calculator") that only estimates a fare for one hard-coded rule set and prints a ticket. See `README.md`. Not used by the web app. |
| `TravelReservationSystem/TRAVEL SYSTEM.py`, `app_backup.py`, `templates/reservation_backup.html` | Frozen older snapshots of the Flask app. Dead code kept for reference; nothing imports them. |

---

## 2. File structure

```
Travel-reservation-project/
├── README.md                     Docs for the desktop prototype (not the web app)
├── main.py                       Desktop pywebview fare calculator (prototype)
├── map.html                      Leaflet map UI for the desktop prototype
├── ticket.html                   Ticket markup for the desktop prototype
├── requirements.txt              Desktop prototype dependencies (pywebview, PyQt6…)
├── fare_settings.db              SQLite DB belonging to the desktop prototype
│
└── TravelReservationSystem/      ← THE WEB APPLICATION
    ├── app.py                    Entire backend: routes, auth, fare engine,
    │                             geocoding, routing, DB schema + migrations
    ├── travel_reservation.db     SQLite database (created/migrated on startup)
    ├── requirements.txt          Flask, qrcode, Pillow, gunicorn
    ├── python-version            Pinned interpreter marker
    ├── TRAVEL SYSTEM.py          Legacy snapshot — unused
    ├── app_backup.py             Legacy snapshot — unused
    │
    ├── static/
    │   ├── js/
    │   │   └── fare-calculator.js   Shared front-end pricing module. Reads the
    │   │                            fare settings off the <option> attributes
    │   │                            and mirrors the server formula exactly.
    │   ├── css/
    │   │   └── style.css            All styling (glassmorphism theme)
    │   ├── assets/
    │   │   └── Background.jpg       Hero background image
    │   └── leaflet/
    │       ├── leaflet.js           Vendored Leaflet (map rendering)
    │       └── leaflet.css
    │
    └── templates/
        ├── login.html               Customer/admin sign-in
        ├── register.html            Customer sign-up
        ├── verify.html              Public page a scanned ticket QR opens
        ├── dashboard.html           Customer's own bookings
        ├── reservation.html         ★ Booking form + live fare estimate + map
        ├── edit_reservation.html    ★ Edit an existing booking (same engine)
        ├── receipt.html             Payment receipt for one booking
        ├── ticket.html              Per-passenger printable ticket
        ├── admin_login.html         Admin sign-in
        ├── admin.html               ★ Admin overview + per-type pricing cards
        ├── admin_vehicle_types.html Vehicle type list
        ├── admin_vehicle_type_form.html  ★ Add/edit one type's fare settings
        ├── admin_vehicles.html      Individual vehicle fleet list
        ├── admin_vehicle_form.html  Add/edit one vehicle
        └── reservation_backup.html  Legacy snapshot — unused
```

★ = files central to the fare engine.

---

## 3. Data model (`travel_reservation.db`)

Seven tables, all created and migrated in code by `init_database()`
[app.py:634](TravelReservationSystem/app.py#L634) — deleting the `.db` file is never
required to pick up a schema change.

**`vehicle_types`** — the pricing table. One row per type; the fare engine reads
only these columns, so a new type needs no code change.

| Column | Meaning |
|---|---|
| `type_name` | Display name, unique (`Bus`, `Private Van`, `Taxi`, …) |
| `base_fare` | Flat charge for the trip |
| `included_distance` | Kilometres covered by the base fare |
| `rate_per_km` | Charge per km **beyond** `included_distance` |
| `min_fare` | Floor price; `0` means no floor |
| `extra_charges`, `extra_charges_label` | Optional flat add-on (terminal fee, toll…) and the wording shown to the customer |
| `charge_basis` | `per_booking` (one price for the vehicle) or `per_passenger` (× passengers) |
| `max_passengers` | Seat capacity used by seat assignment |
| `location_type` | `land` / `air` / `sea` — informational label |
| `is_available` | Admin switch: is this type offered at all |
| `fare_configured` | Has an admin actually set pricing. A type with `fare_configured = 0` **cannot be booked** |

Current rows: `Bus` (₱2.22/km, per passenger, 45 seats), `Van` (₱2.00/km, per
passenger, 12 seats, currently `is_available = 0`), `Private Van` (₱1,500 base /
first 25 km / ₱45 per extra km, per booking, 10 seats), `Taxi` (₱13.50/km, per
passenger, 4 seats).

**`reservations`** — one row per booking: `booking_reference`, user, passenger
names, `starting_location` / `origin` / `destination`, date, time, `vehicle`,
`passengers`, **`distance`**, **`fare`**, `status`, `vehicle_code`. `distance` and
`fare` are written once at booking time and are *never* recomputed from the
current pricing, so a later admin reprice cannot change an existing quote.

**`tickets`** — one row per passenger, linked by `reservation_id`. Carries its own
`ticket_number` (unique), `seat_number`, `fare` (per passenger), and `status`.

**`users`** — `full_name`, `username` (unique), `password`, `contact`.

**`vehicles`** — the physical fleet: `vehicle_code`, `vehicle_type`, plate,
capacity, availability status, assigned driver.

**`location_cache`** — address text → lat/lon, so repeated Nominatim lookups don't
hammer the public service.

**`route_cache`** — (start, destination, vehicle type) → road distance from OSRM.

---

## 4. How the fare calculation works

### The formula — one implementation, every vehicle type

```
extra_distance = max(0, total_distance − included_distance)
trip_fare      = max(min_fare, base_fare + extra_distance × rate_per_km)
total_fare     = trip_fare × passengers + extra_charges   if charge_basis = per_passenger
               = trip_fare           + extra_charges      if charge_basis = per_booking
```

Note the ordering: the minimum-fare floor is applied **per trip, before** the
passenger multiplier, and `extra_charges` is added **after**, for both bases. So a
per-passenger type with a floor charges `floor × passengers`, not `floor` once.

`get_fare_breakdown()` [app.py:856](TravelReservationSystem/app.py#L856) is the
**only** place this math exists on the server. It takes a type name, a distance and
a passenger count, looks up that type's `vehicle_types` row, and returns a full
breakdown object. It raises `FareNotConfigured`
([app.py:846](TravelReservationSystem/app.py#L846)) for an unknown or unpriced type
instead of guessing a number.

The browser runs the identical formula from
[static/js/fare-calculator.js](TravelReservationSystem/static/js/fare-calculator.js).
It never contains a price of its own — `readFareSettings()` reads `data-base-fare`,
`data-included-distance`, `data-rate-per-km`, `data-min-fare`,
`data-extra-charges`, `data-charge-basis` off the selected `<option>`, and those
attributes are rendered straight from the database by the Jinja template. Add a
vehicle type in the admin UI and it is priced correctly with zero source edits.

### Where the distance comes from

`resolve_trip_distance()` [app.py:1042](TravelReservationSystem/app.py#L1042)
prefers real roads over straight lines:

1. If the form carries resolved `pickup_lat/lon` and `destination_lat/lon`, ask
   **OSRM** (`fetch_osrm_route`, [app.py:998](TravelReservationSystem/app.py#L998))
   for the driving distance and use it.
2. Otherwise fall back to the **haversine** straight-line distance between the two
   geocoded addresses (`haversine_km`, [app.py:160](TravelReservationSystem/app.py#L160)).
3. If only free-text locations are available, use the cached name→distance table.

Whatever the browser submitted is then **sanity-clamped** to
`[straight_km, straight_km × 3]` and capped at `MAX_TRIP_KM = 2000`, so a tampered
or stale distance cannot price a 3 km trip as 300 km.

### Server-authoritative, end to end

The POST handler in `reservation()` [app.py:1457](TravelReservationSystem/app.py#L1457)
never reads a price from the form. It re-validates the vehicle type, re-checks
`fare_configured` and `is_available`, re-resolves the distance, then calls
`get_fare_breakdown()` and stores `breakdown["total_fare"]`. The same applies to
`edit_reservation()` [app.py:1798](TravelReservationSystem/app.py#L1798): when the
pickup/origin/destination are unchanged the stored distance is reused, otherwise
the trip is re-measured and repriced.

Distance is carried at **2 decimal places everywhere** — the hidden input's
`step="0.01"`, the JS `toFixed(2)`, the DB, and the `%.2f` receipt format — so the
figure quoted in the browser and the figure billed by the server are the same number.

### Type availability gate

`bookable = fare_configured AND is_available`. Only bookable types are offered in
the customer picker [app.py:1626](TravelReservationSystem/app.py#L1626). If an admin
creates a type without pricing it, the toggle route refuses to switch it on and
redirects back to the fare form, and the admin list shows it as
**"Needs pricing"**. Nothing is silently assigned a wrong fare.

---

## 5. Walk-through: one booking

1. **Register / log in** — `POST /register` [app.py:1205](TravelReservationSystem/app.py#L1205),
   `POST /` [app.py:1162](TravelReservationSystem/app.py#L1162). Passwords are
   SHA-256 hashed (`hash_password`, [app.py:187](TravelReservationSystem/app.py#L187));
   identity lives in the Flask session (`user_id`, `username`, `is_admin`).
2. **Open the booking form** — `GET /reservation` renders the vehicle picker from
   `get_available_vehicle_types()` [app.py:1078](TravelReservationSystem/app.py#L1078),
   each option labelled by `fare_price_label()`
   ([app.py:930](TravelReservationSystem/app.py#L930)), e.g.
   `Private Van — ₱1,500.00 base (first 25 km) · ₱45.00/km after 25 km · per booking`.
3. **Pick addresses on the map or by search** — the typeahead calls
   `GET /api/search-address` [app.py:1340](TravelReservationSystem/app.py#L1340)
   (Nominatim, results cached in `location_cache`). Once both endpoints resolve,
   `GET /api/calculate-route` [app.py:1388](TravelReservationSystem/app.py#L1388)
   returns the OSRM road polyline and distance; the map draws it and the distance
   field is filled.
4. **Watch the estimate update** — `GET /api/calculate-fare`
   [app.py:1428](TravelReservationSystem/app.py#L1428) and the local
   `fare-calculator.js` recompute on every change to pickup, destination, vehicle
   or passenger count. The breakdown (base, included km, extra km, add-ons, total)
   is shown, marked as an **estimate**.
5. **Confirm** — `POST /reservation` validates names against the passenger count,
   rejects unavailable/unpriced types, resolves distance server-side, computes the
   fare, inserts the reservation with a `BKF-YYYYMMDD-NNNN` reference
   (`generate_booking_reference`, [app.py:835](TravelReservationSystem/app.py#L835)).
6. **Seats and tickets** — `assign_seats()` [app.py:401](TravelReservationSystem/app.py#L401)
   treats "the same trip" as the tuple (starting location, origin, destination,
   date, time, vehicle) and hands out the first free seats in it, ignoring
   cancelled tickets so seats recycle. `create_tickets_for_reservation()`
   [app.py:498](TravelReservationSystem/app.py#L498) then writes one `tickets` row
   per passenger — idempotent, so no duplicates on a double submit.
7. **Print / verify** — `GET /ticket/<ticket_number>`
   [app.py:2125](TravelReservationSystem/app.py#L2125) renders the boarding pass,
   `GET /receipt/<ticket_number>` [app.py:2177](TravelReservationSystem/app.py#L2177)
   the receipt, `GET /ticket/<n>/qr.png` [app.py:2222](TravelReservationSystem/app.py#L2222)
   encodes the verification URL, and `GET /verify/<n>`
   [app.py:2279](TravelReservationSystem/app.py#L2279) is the public page the QR
   opens. The ticket, receipt and booking all read the *same stored* fare.
8. **Change or cancel** — `POST /reservation/cancel/<id>`
   [app.py:1996](TravelReservationSystem/app.py#L1996) and `delete` free the seats
   again; both scope the row by `session["user_id"]` so a customer cannot touch
   someone else's booking.

---

## 6. Admin side

Sign in at `/admin-login` [app.py:1274](TravelReservationSystem/app.py#L1274).

| Area | Route | What it does |
|---|---|---|
| Overview | `/admin` [app.py:1646](TravelReservationSystem/app.py#L1646) | Bookings, revenue, per-type pricing cards with bookable / disabled / needs-pricing badges |
| Vehicle types | `/admin/vehicle-types` [app.py:2416](TravelReservationSystem/app.py#L2416) | List all types with their price label |
| Add a type | `/admin/vehicle-types/new` [app.py:2427](TravelReservationSystem/app.py#L2427) | Name + full pricing form in one step; duplicate names flash an error |
| Price a type | `/admin/vehicle-types/edit/<id>` [app.py:2484](TravelReservationSystem/app.py#L2484) | Edit rates; existing bookings keep the fare they were quoted |
| Enable/disable | `/admin/vehicle-types/toggle/<id>` [app.py:2529](TravelReservationSystem/app.py#L2529) | Refuses to enable a type that has no pricing |
| Fleet | `/admin/vehicles`, `/add`, `/edit/<id>`, `/delete/<id>` | Individual vehicles, plates, drivers, availability |
| Bookings | `/admin/delete-reservation/<id>` [app.py:2093](TravelReservationSystem/app.py#L2093) | Remove a booking as admin |

**Validation** — `read_fare_form()` [app.py:2366](TravelReservationSystem/app.py#L2366)
rejects non-numeric or negative amounts, an out-of-range `max_passengers` (must be
1–500), an unknown `charge_basis` or `location_type`, and any attempt to save a
type with no charge at all ("Set at least one charge …"). Fare labels are truncated
to 60 characters. Every admin mutation is a `POST`.

---

## 7. Route reference

| Method | Path | Access |
|---|---|---|
| GET/POST | `/` | login |
| GET/POST | `/register` | public |
| GET/POST | `/admin-login` | public |
| GET | `/dashboard` | customer |
| GET | `/api/search-address` | any |
| GET | `/api/calculate-route` | any |
| GET | `/api/calculate-fare` | any |
| GET/POST | `/reservation` | customer |
| GET/POST | `/reservation/edit/<id>` | owner |
| POST | `/reservation/cancel/<id>` · `/reservation/delete/<id>` | owner |
| GET | `/ticket/<n>` · `/receipt/<n>` · `/ticket/<n>/qr.png` | holder |
| GET | `/verify/<n>` | public |
| GET/POST | `/admin`, `/admin/vehicle-types*`, `/admin/vehicles*` | admin |
| GET | `/logout` | any signed-in |

---

## 8. Running it

```bash
cd Travel-reservation-project
python -m venv .venv
.venv/bin/pip install -r TravelReservationSystem/requirements.txt

cd TravelReservationSystem
../.venv/bin/python app.py          # http://127.0.0.1:5000
```

Admin credentials out of the box: `admin` / `admin123`
([app.py:1282](TravelReservationSystem/app.py#L1282)).

The schema and the seeded admin are created at *import* time, so the app also runs
under a WSGI launcher — `flask --app app run`, or `gunicorn app:app` — not only via
`python app.py`.

Two gotchas worth knowing:
- Use the project's `.venv/bin/python`; the system Python has no Flask.
- If you serve it on a non-standard port for testing, avoid 5061/5062 — Chrome
  blocks them as unsafe ports. 8090 works.

---

## 9. External services

| Service | Used for | Notes |
|---|---|---|
| [Nominatim](https://nominatim.openstreetmap.org) | address → coordinates | free, rate-limited to ~1 request/s; results cached in `location_cache` |
| [OSRM demo](https://router.project-osrm.org) | road distance + polyline | demo server, no availability guarantee; cached in `route_cache` |
| OpenStreetMap tiles | map rendering | requires internet |

The app degrades gracefully: if geocoding or routing is unreachable it falls back
to straight-line distance and still produces a fare.

---

## 10. Design rules this codebase follows

- **No hardcoded prices anywhere.** The old `VEHICLE_RATES`, `VEHICLE_LIMITS` and
  `VEHICLE_CAPACITY` dictionaries are gone; the database is the only source.
- **One formula, two renderings.** The server engine and `fare-calculator.js` must
  stay in sync; the JS reads its coefficients from the DOM, never from literals.
- **The server is the authority.** Browser-submitted distance and fare are always
  re-derived before anything is written.
- **Quotes are frozen.** `reservations.fare` is a snapshot, not a view over the
  current rate card.
- **Unpriced means unbookable.** A new type is inert until an admin prices it.
- **Migrations are in-code and idempotent** (`add_missing_column`,
  `migrate_legacy_fare_columns`), so the DB self-heals on start.
