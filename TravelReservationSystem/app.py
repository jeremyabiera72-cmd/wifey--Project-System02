from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    Response,
    jsonify
)
import sqlite3
import hashlib
import io
import base64
import json
import math
import os
import urllib.request
import urllib.parse
import qrcode
import secrets
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = "travel_reservation_secret_key"

DATABASE = os.path.join(BASE_DIR, "travel_reservation.db")

# Vehicle types, capacities and every price live in the vehicle_types table so
# the admin can add a type without a code change. These are the only allowed
# values for the columns that choose how a fare is assembled.
CHARGE_BASES = ("per_passenger", "per_booking")
LOCATION_TYPES = ("land", "air", "sea")

# Sanity bounds for a trip distance the server has to accept without re-routing.
MAX_TRIP_KM = 2000.0
ROAD_FACTOR = 3.0

LAND_LOCATIONS = ['Molave', 'Pagadian City', 'Ipil', 'Zamboanga City', 'Dipolog City', 'Dapitan City', 'Iligan City', 'Ozamiz City', 'Cagayan de Oro City', 'Malaybalay City', 'Valencia City', 'Gingoog City', 'Butuan City', 'Surigao City', 'Davao City', 'Tagum City', 'Panabo City', 'Digos City', 'Mati City', 'General Santos City', 'Koronadal City', 'Kidapawan City', 'Tacurong City', 'Cotabato City', 'Alicia', 'Buug', 'Diplahan', 'Imelda', 'Kabasalan', 'Mabuhay', 'Malangas', 'Naga', 'Olutanga', 'Payao', 'Roseller Lim', 'Siay', 'Talusan', 'Tungawan', 'Aurora', 'Dumingag', 'Guipos', 'Josefina', 'Kumalarang', 'Labangan', 'Lakewood', 'Lapuyan', 'Mahayag', 'Midsalip', 'Ramon Magsaysay', 'San Miguel', 'San Pablo', 'Sominot', 'Tabina', 'Tambulig', 'Tukuran', 'Vincenzo A. Sagun', 'Aloran', 'Baliangao', 'Bonifacio', 'Calamba', 'Clarin', 'Concepcion', 'Don Victoriano Chiongbian', 'Jimenez', 'Lopez Jaena', 'Panaon', 'Plaridel', 'Sapang Dalaga', 'Sinacaban', 'Tangub City', 'Tudela', 'Baungon', 'Cabanglasan', 'Damulog', 'Dangcagan', 'Don Carlos', 'Impasug-ong', 'Kibawe', 'Kitaotao', 'Lantapan', 'Libona', 'Malitbog', 'Manolo Fortich', 'Maramag', 'Pangantucan', 'Quezon', 'San Fernando', 'Sumilao', 'Talakag', 'Asuncion', 'Braulio E. Dujali', 'Carmen', 'Kapalong', 'Laak', 'Maco', 'Mawab', 'Monkayo', 'Montevista', 'New Bataan', 'New Corella', 'San Isidro', 'Santo Tomas', 'Talaingod', 'Baganga', 'Banaybanay', 'Boston', 'Caraga', 'Cateel', 'Lupon', 'Manay', 'Governor Generoso', 'Bansalan', 'Hagonoy', 'Kiblawan', 'Magsaysay', 'Malalag', 'Padada', 'Santa Cruz', 'Sulop', 'Alabel', 'Glan', 'Kiamba', 'Maasim', 'Malapatan', 'Malungon', 'Polomolok', 'Sarangani', 'Tupi', 'Banga', 'Lake Sebu', 'Norala', 'Santo Nino', 'Surallah', 'Tampakan', 'Tantangan', 'Tboli', 'Arakan', 'Banisilan', 'Kabacan', 'Libungan', 'Matalam', 'Makilala', 'Magpet', 'Mlang', 'Midsayap', 'Pigcawayan', 'Pikit', 'President Roxas', 'Aleosan', 'Alamada', 'Antipas', 'Buldon', 'Datu Abdullah Sangki', 'Datu Anggal Midtimbang', 'Datu Blah T. Sinsuat', 'Datu Hoffer Ampatuan', 'Datu Montawal', 'Datu Odin Sinsuat', 'Datu Paglas', 'Datu Piang', 'Datu Salibo', 'Datu Saudi Ampatuan', 'Datu Unsay', 'General Salipada K. Pendatun', 'Guindulungan', 'Kadayangan', 'Lambayong', 'Lantawan', 'Maguing', 'Malabang', 'Matanog', 'Pagalungan', 'Pagagawan', 'Parang', 'Patikul', 'Picong', 'Rajah Buayan', 'Sultan Kudarat', 'Sultan Mastura', 'Talayan', 'Upi', 'Wao', 'Buenavista', 'Cabadbaran City', 'Claver', 'Dinagat', 'Esperanza', 'Gigaquit', 'Hinatuan', 'Jabonga', 'Kitcharao', 'Las Nieves', 'Lianga', 'Loreto', 'Madrid', 'Mainit', 'Malimono', 'Nasipit', 'Placer', 'Prosperidad', 'San Francisco', 'San Francisco (Agusan del Sur)', 'San Francisco, Agusan del Sur', 'Bayugan City', 'Trento', 'Rosario', 'Bunawan', 'San Jose', 'San Luis', 'Santa Monica', 'Sibagat', 'Sison', 'Socorro', 'Tagana-an', 'Tubod', 'Veruela', 'Bacuag', 'Basilisa', 'Carrascal', 'Cortes', 'Del Carmen', 'Dapa', 'General Luna', 'Libjo', 'Limasawa', 'Pilar', 'San Benito', 'San Juan', 'Surigao del Norte', 'Tago', 'Barobo', 'Bayabas', 'Cagwait', 'Lanuza', 'Lingig', 'Marihatag', 'San Agustin', 'Tagbina', 'Tandag City']
AIRPORT_LOCATIONS = ["Zamboanga International Airport","Pagadian Airport","Dipolog Airport","Laguindingan Airport","Labo Airport (Ozamiz)","Francisco Bangoy International Airport","General Santos International Airport","Cotabato Airport","Butuan Airport","Surigao Airport","Siargao Airport","Tandag Airport"]
PORT_LOCATIONS = ["Port of Zamboanga","Port of Iligan","Port of Cagayan de Oro","Port of Ozamiz","Port of Davao","Port of General Santos","Port of Surigao","Port of Dapitan","Port of Nasipit"]
ALL_MINDANAO_LAND_LOCATIONS = sorted(set(LAND_LOCATIONS))

BARANGAYS_BY_CITY = {
    'San Francisco (Agusan del Sur)': ['Poblacion', 'Alegria', 'Barangay 1', 'Barangay 2', 'Barangay 3', 'Barangay 4', 'Barangay 5', 'Bayugan 2', 'Bitan-agan', 'Borbon', 'Buenas Suerte', 'Caimpugan', 'Das-agan', 'Ebro', 'Hubang', 'Karaos', 'Ladgadan', 'Lapinigan', 'Lucena', 'Mate', 'New Visayas', 'Ormaca', 'Pasta', 'Pisa-an', 'Rizal', 'San Isidro', 'Santa Ana', 'Tagapua'],
    'San Francisco': ['Poblacion', 'Alegria', 'Barangay 1', 'Barangay 2', 'Barangay 3', 'Barangay 4', 'Barangay 5', 'Bayugan 2', 'Bitan-agan', 'Borbon', 'Buenas Suerte', 'Caimpugan', 'Das-agan', 'Ebro', 'Hubang', 'Karaos', 'Ladgadan', 'Lapinigan', 'Lucena', 'Mate', 'New Visayas', 'Ormaca', 'Pasta', 'Pisa-an', 'Rizal', 'San Isidro', 'Santa Ana', 'Tagapua'],
    'Bayugan City': ['Poblacion', 'Taglatawan', 'Maygatasan', 'Bucac', 'Fili', 'Gamao', 'Hamogaway', 'Katipunan', 'Mabuhay', 'Marcelina', 'Mt. Carmel', 'Mt. Olive', 'Mt. Ararat', 'Noli', 'Osmeña', 'Panay', 'Sagmone', 'Saguma', 'Salvacion', 'San Adolf', 'San Isidro', 'Santa Irene', 'Verdu'],
    'Prosperidad': ['Poblacion', 'Patin-ay', 'Aurora', 'Awa', 'Azpetia', 'La Caridad', 'La Perian', 'La Purisima', 'La Suerte', 'La Union', 'Las Navas', 'Los Arcos', 'Lucena', 'Mabuhay', 'Magsaysay', 'Mapaga', 'New Maug', 'Napo', 'Salimbogaon', 'Salvacion', 'San Joaquin', 'San Jose', 'San Martin', 'San Pedro', 'San Rafael', 'San Salvador', 'San Vicente', 'Santa Irene', 'Santa Maria'],
    'Trento': ['Poblacion', 'Basa', 'Cuevas', 'Kapatagan', 'Langkilaan', 'Manat', 'New Mateo', 'Pangyan', 'Pulang-lupa', 'Salvacion', 'San Ignacio', 'San Isidro', 'San Roque', 'Santa Maria', 'Tudela'],
    'Rosario': ['Poblacion', 'Bayugan 3', 'Cabantao', 'Cabawan', 'Marfil', 'Novele', 'Santa Cruz', 'Tagbayagan', 'Wasian'],
    'Bunawan': ['Poblacion', 'Bunawan Brook', 'Consuelo', 'Libertad', 'Mambalili', 'Nueva Era', 'San Andres', 'San Marcos', 'San Teodoro'],
    'Esperanza': ['Poblacion', 'Agsabu', 'Bakingking', 'Bentahon', 'Bunaguit', 'Catmonon', 'Cebulan', 'Dakutan', 'Duangan', 'Guadalupe', 'Hawilian', 'Labao', 'Maasin', 'Mahagkot', 'Milagros', 'Nato', 'New Gingoog', 'Oro', 'Remedios', 'Salug', 'San Toribio', 'Santa Fe', 'Segunda', 'Sinakungan', 'Tandang Sora', 'Tahina', 'Tres Reyes', 'Valentine', 'Piglawigan'],
    'Sibagat': ['Poblacion', 'Anislagan', 'Banagbanag', 'Del Rosario', 'El Rio', 'Ilihan', 'Kauswagan', 'Kioya', 'Magkalape', 'Magsaysay', 'Mahayahay', 'New Tubigon', 'Padiay', 'Perez', 'San Isidro', 'San Vicente', 'Santa Cruz', 'Santa Maria', 'Sinai', 'Tabontabon', 'Tag-oyango', 'Villangit'],
    'Digos City': ['Digos City Proper', 'Aplaya', 'Balabag', 'Badiang', 'Binaton', 'Cogon', 'Colorado', 'Dawis', 'Kapatagan', 'Kiagot', 'Mahayahay', 'Matti', 'Rizal', 'San Jose', 'San Miguel', 'Sinawilan', 'Soong', 'Tiguman'],
    'Davao City': ['Davao City Proper', 'Buhangin', 'Calinan', 'Toril', 'Tugbok', 'Paquibato', 'Baguio', 'Agdao', 'Bajada', 'Matina', 'Talomo'],
    'Iligan City': ['Iligan City Proper', 'Acmac', 'Bagong Silang', 'Buru-un', 'Dalipuga', 'Hinaplanon', 'Kiwalan', 'Luinab', 'Pala-o', 'Poblacion', 'Tibanga', 'Tipanoy'],
    'Cagayan de Oro City': ['Cagayan de Oro City Proper', 'Agusan', 'Balulang', 'Bugo', 'Bulua', 'Carmen', 'Gusa', 'Iponan', 'Lapasan', 'Lumbia', 'Macasandig', 'Puerto', 'Tignapoloan'],
    'General Santos City': ['General Santos City Proper', 'Apopong', 'Bula', 'Calumpang', 'Conel', 'Fatima', 'Labangal', 'Lagao', 'San Isidro', 'Tambler'],
    'Butuan City': ['Butuan City Proper', 'Ampayon', 'Baan', 'Bancasi', 'Buhang', 'Doongan', 'Dumalagan', 'Langihan', 'Libertad', 'Obrero'],
    'Surigao City': ['Surigao City Proper', 'Anomar', 'Catadman', 'Ipil', 'Luna', 'Mat-i', 'San Isidro', 'Washington'],
    'Cotabato City': ['Cotabato City Proper', 'Bagua', 'Kalanganan', 'Kalanganan II', 'Kamagayan', 'Mother Bagua', 'Rosary Heights', 'Tamontaka'],
    'Zamboanga City': ['Zamboanga City Proper', 'Ayala', 'Baliwasan', 'Canelar', 'Guiwan', 'Mercedes', 'Putik', 'Recodo', 'San Roque', 'Tetuan'],
    'Ozamiz City': ['Ozamiz City Proper', 'Aguada', 'Bongbong', 'Capucao', 'Catadman', 'Maningcol', 'Malaubang', 'Sinuza'],
    'Dipolog City': ['Dipolog City Proper', 'Barra', 'Biasong', 'Central', 'Cogon', 'Galas', 'Miputak', 'Olingan'],
    'Pagadian City': ['Pagadian City Proper', 'Balangasan', 'Bogo', 'Dao', 'Kawit', 'San Francisco', 'Tiguma'],
    'Malaybalay City': ['Malaybalay City Proper', 'Aglayan', 'Bangcud', 'Cabangahan', 'Casisang', 'Kalasungay', 'Laguitas', 'San Jose'],
    'Marawi City': ['Marawi City Proper', 'Banggolo', 'Boganga', 'Datu Saber', 'Lumbaca Madaya', 'Sagonsongan', 'Tuca'],
    'Tagum City': ['Tagum City Proper', 'Apokon', 'Bincungan', 'Canocotan', 'Cuambogan', 'La Filipina', 'Magugpo', 'Mankilam', 'Visayan Village'],
    'Molave': ['Molave Proper'],
    'Ipil': ['Ipil Proper'],
    'Dapitan City': ['Dapitan City Proper'],
    'Valencia City': ['Valencia City Proper'],
    'Gingoog City': ['Gingoog City Proper'],
    'Panabo City': ['Panabo City Proper'],
    'Mati City': ['Mati City Proper'],
    'Koronadal City': ['Koronadal City Proper'],
    'Kidapawan City': ['Kidapawan City Proper'],
    'Tacurong City': ['Tacurong City Proper']
}

TERMINALS_BY_CITY = {'Molave': ['Molave Bus Terminal', 'Molave Van Terminal'], 'Pagadian City': ['Pagadian City Bus Terminal', 'Pagadian City Van Terminal'], 'Ipil': ['Ipil Bus Terminal', 'Ipil Van Terminal'], 'Zamboanga City': ['Zamboanga City Bus Terminal', 'Zamboanga City Van Terminal'], 'Dipolog City': ['Dipolog City Bus Terminal', 'Dipolog City Van Terminal'], 'Dapitan City': ['Dapitan City Bus Terminal', 'Dapitan City Van Terminal'], 'Iligan City': ['Iligan City Bus Terminal', 'Iligan City Van Terminal'], 'Ozamiz City': ['Ozamiz City Bus Terminal', 'Ozamiz City Van Terminal'], 'Cagayan de Oro City': ['Cagayan de Oro City Bus Terminal', 'Cagayan de Oro City Van Terminal'], 'Malaybalay City': ['Malaybalay City Bus Terminal', 'Malaybalay City Van Terminal'], 'Valencia City': ['Valencia City Bus Terminal', 'Valencia City Van Terminal'], 'Gingoog City': ['Gingoog City Bus Terminal', 'Gingoog City Van Terminal'], 'Butuan City': ['Butuan City Bus Terminal', 'Butuan City Van Terminal'], 'Surigao City': ['Surigao City Bus Terminal', 'Surigao City Van Terminal'], 'Davao City': ['Davao City Bus Terminal', 'Davao City Van Terminal'], 'Tagum City': ['Tagum City Bus Terminal', 'Tagum City Van Terminal'], 'Panabo City': ['Panabo City Bus Terminal', 'Panabo City Van Terminal'], 'Digos City': ['Digos City Bus Terminal', 'Digos City Van Terminal'], 'Mati City': ['Mati City Bus Terminal', 'Mati City Van Terminal'], 'General Santos City': ['General Santos City Bus Terminal', 'General Santos City Van Terminal'], 'Koronadal City': ['Koronadal City Bus Terminal', 'Koronadal City Van Terminal'], 'Kidapawan City': ['Kidapawan City Bus Terminal', 'Kidapawan City Van Terminal'], 'Tacurong City': ['Tacurong City Bus Terminal', 'Tacurong City Van Terminal'], 'Cotabato City': ['Cotabato City Bus Terminal', 'Cotabato City Van Terminal'], 'San Francisco (Agusan del Sur)': ['San Francisco Integrated Bus Terminal', 'San Francisco Van Terminal'], 'San Francisco': ['San Francisco Integrated Bus Terminal', 'San Francisco Van Terminal']}

LOCATION_COORDINATES = {
    'San Francisco (Agusan del Sur)': (8.505, 125.978),
    'San Francisco, Agusan del Sur': (8.505, 125.978),
    'Hubang': (8.512, 125.972),
    'Alegria': (8.489, 125.961),
    'Borbon': (8.472, 125.983),
    'Lapinigan': (8.538, 125.941),
    'Bayugan 2': (8.542, 125.989),
    'Santa Ana': (8.486, 125.992),
    'Karaos': (8.509, 125.968),
    'Ladgadan': (8.520, 125.985),
    'Lucena': (8.560, 125.935),
    'Mate': (8.461, 125.955),
    'New Visayas': (8.525, 125.963),
    'Ormaca': (8.517, 125.950),
    'Pasta': (8.530, 125.990),
    'Pisa-an': (8.495, 125.960),
    'Tagapua': (8.455, 125.970),
    'Bitan-agan': (8.500, 125.990),
    'Buenas Suerte': (8.510, 126.010),
    'Caimpugan': (8.480, 125.940),
    'Das-agan': (8.525, 125.945),
    'Ebro': (8.535, 125.975),
    'Bayugan City': (8.745, 125.748),
    'Prosperidad': (8.598, 125.918),
    'Patin-ay': (8.592, 125.925),
    'Trento': (8.048, 126.063),
    'Rosario': (8.358, 126.012),
    'Bunawan': (8.172, 125.992),
    'Esperanza': (8.678, 125.648),
    'Sibagat': (8.818, 125.698),
    'Molave': (7.858, 123.424), 'Pagadian City': (7.8257, 123.437), 'Ipil': (7.785, 122.586), 'Zamboanga City': (6.9214, 122.079), 'Dipolog City': (8.588, 123.34), 'Dapitan City': (8.654, 123.424), 'Iligan City': (8.228, 124.245), 'Ozamiz City': (8.148, 123.84), 'Cagayan de Oro City': (8.4542, 124.6319), 'Malaybalay City': (8.1575, 125.1278), 'Valencia City': (7.9064, 125.095), 'Gingoog City': (8.828, 125.102), 'Butuan City': (8.9475, 125.5406), 'Surigao City': (9.789, 125.495), 'Davao City': (7.0707, 125.6087), 'Tagum City': (7.4478, 125.8078), 'Panabo City': (7.3081, 125.684), 'Digos City': (6.7497, 125.3572), 'Mati City': (6.955, 126.216), 'General Santos City': (6.1164, 125.1716), 'Koronadal City': (6.5, 124.846), 'Kidapawan City': (7.008, 125.089), 'Tacurong City': (6.692, 124.676), 'Cotabato City': (7.2236, 124.246), 'Zamboanga International Airport': (6.9224, 122.0598), 'Pagadian Airport': (7.8297, 123.4615), 'Dipolog Airport': (8.601, 123.341), 'Laguindingan Airport': (8.6125, 124.4565), 'Labo Airport (Ozamiz)': (8.178, 123.842), 'Francisco Bangoy International Airport': (7.125, 125.645), 'General Santos International Airport': (6.058, 125.096), 'Cotabato Airport': (7.1656, 124.2097), 'Butuan Airport': (8.9515, 125.477), 'Surigao Airport': (9.756, 125.48), 'Siargao Airport': (9.8591, 126.014), 'Tandag Airport': (9.0725, 126.171), 'Port of Zamboanga': (6.905, 122.08), 'Port of Iligan': (8.228, 124.245), 'Port of Cagayan de Oro': (8.485, 124.659), 'Port of Ozamiz': (8.15, 123.842), 'Port of Davao': (7.073, 125.617), 'Port of General Santos': (6.111, 125.171), 'Port of Surigao': (9.784, 125.49), 'Port of Dapitan': (8.656, 123.425), 'Port of Nasipit': (8.969, 125.292), 'Digos City Proper': (6.7497, 125.3572), 'Aplaya': (6.7497, 125.3572), 'Balabag': (6.7497, 125.3572), 'Badiang': (6.7497, 125.3572), 'Binaton': (6.7497, 125.3572), 'Cogon': (6.7497, 125.3572), 'Colorado': (6.7497, 125.3572), 'Dawis': (6.7497, 125.3572), 'Kapatagan': (6.7497, 125.3572), 'Kiagot': (6.7497, 125.3572), 'Mahayahay': (6.7497, 125.3572), 'Matti': (6.7497, 125.3572), 'Rizal': (6.7497, 125.3572), 'San Jose': (6.7497, 125.3572), 'San Miguel': (6.7497, 125.3572), 'Sinawilan': (6.7497, 125.3572), 'Soong': (6.7497, 125.3572), 'Tiguman': (6.7497, 125.3572), 'Davao City Proper': (7.0707, 125.6087), 'Buhangin': (7.0707, 125.6087), 'Calinan': (7.0707, 125.6087), 'Toril': (7.0707, 125.6087), 'Tugbok': (7.0707, 125.6087), 'Paquibato': (7.0707, 125.6087), 'Baguio': (7.0707, 125.6087), 'Agdao': (7.0707, 125.6087), 'Bajada': (7.0707, 125.6087), 'Matina': (7.0707, 125.6087), 'Talomo': (7.0707, 125.6087), 'Iligan City Proper': (8.228, 124.245), 'Acmac': (8.228, 124.245), 'Bagong Silang': (8.228, 124.245), 'Buru-un': (8.228, 124.245), 'Dalipuga': (8.228, 124.245), 'Hinaplanon': (8.228, 124.245), 'Kiwalan': (8.228, 124.245), 'Luinab': (8.228, 124.245), 'Pala-o': (8.228, 124.245), 'Poblacion': (8.228, 124.245), 'Tibanga': (8.228, 124.245), 'Tipanoy': (8.228, 124.245), 'Cagayan de Oro City Proper': (8.4542, 124.6319), 'Agusan': (8.4542, 124.6319), 'Balulang': (8.4542, 124.6319), 'Bugo': (8.4542, 124.6319), 'Bulua': (8.4542, 124.6319), 'Carmen': (8.4542, 124.6319), 'Gusa': (8.4542, 124.6319), 'Iponan': (8.4542, 124.6319), 'Lapasan': (8.4542, 124.6319), 'Lumbia': (8.4542, 124.6319), 'Macasandig': (8.4542, 124.6319), 'Puerto': (8.4542, 124.6319), 'Tignapoloan': (8.4542, 124.6319), 'General Santos City Proper': (6.1164, 125.1716), 'Apopong': (6.1164, 125.1716), 'Bula': (6.1164, 125.1716), 'Calumpang': (6.1164, 125.1716), 'Conel': (6.1164, 125.1716), 'Fatima': (6.1164, 125.1716), 'Labangal': (6.1164, 125.1716), 'Lagao': (6.1164, 125.1716), 'San Isidro': (6.1164, 125.1716), 'Tambler': (6.1164, 125.1716), 'Butuan City Proper': (8.9475, 125.5406), 'Ampayon': (8.9475, 125.5406), 'Baan': (8.9475, 125.5406), 'Bancasi': (8.9475, 125.5406), 'Buhang': (8.9475, 125.5406), 'Doongan': (8.9475, 125.5406), 'Dumalagan': (8.9475, 125.5406), 'Langihan': (8.9475, 125.5406), 'Libertad': (8.9475, 125.5406), 'Obrero': (8.9475, 125.5406), 'Surigao City Proper': (9.789, 125.495), 'Anomar': (9.789, 125.495), 'Catadman': (9.789, 125.495), 'Luna': (9.789, 125.495), 'Mat-i': (9.789, 125.495), 'Washington': (9.789, 125.495), 'Cotabato City Proper': (7.2236, 124.246), 'Bagua': (7.2236, 124.246), 'Kalanganan': (7.2236, 124.246), 'Kalanganan II': (7.2236, 124.246), 'Kamagayan': (7.2236, 124.246), 'Mother Bagua': (7.2236, 124.246), 'Rosary Heights': (7.2236, 124.246), 'Tamontaka': (7.2236, 124.246), 'Zamboanga City Proper': (6.9214, 122.079), 'Ayala': (6.9214, 122.079), 'Baliwasan': (6.9214, 122.079), 'Canelar': (6.9214, 122.079), 'Guiwan': (6.9214, 122.079), 'Mercedes': (6.9214, 122.079), 'Putik': (6.9214, 122.079), 'Recodo': (6.9214, 122.079), 'San Roque': (6.9214, 122.079), 'Tetuan': (6.9214, 122.079), 'Ozamiz City Proper': (8.148, 123.84), 'Aguada': (8.148, 123.84), 'Bongbong': (8.148, 123.84), 'Capucao': (8.148, 123.84), 'Maningcol': (8.148, 123.84), 'Malaubang': (8.148, 123.84), 'Sinuza': (8.148, 123.84), 'Dipolog City Proper': (8.588, 123.34), 'Barra': (8.588, 123.34), 'Biasong': (8.588, 123.34), 'Central': (8.588, 123.34), 'Galas': (8.588, 123.34), 'Miputak': (8.588, 123.34), 'Olingan': (8.588, 123.34), 'Pagadian City Proper': (7.8257, 123.437), 'Balangasan': (7.8257, 123.437), 'Bogo': (7.8257, 123.437), 'Dao': (7.8257, 123.437), 'Kawit': (7.8257, 123.437), 'San Francisco': (8.505, 125.978), 'Tiguma': (7.8257, 123.437), 'Malaybalay City Proper': (8.1575, 125.1278), 'Aglayan': (8.1575, 125.1278), 'Bangcud': (8.1575, 125.1278), 'Cabangahan': (8.1575, 125.1278), 'Casisang': (8.1575, 125.1278), 'Kalasungay': (8.1575, 125.1278), 'Laguitas': (8.1575, 125.1278), 'Tagum City Proper': (7.4478, 125.8078), 'Apokon': (7.4478, 125.8078), 'Bincungan': (7.4478, 125.8078), 'Canocotan': (7.4478, 125.8078), 'Cuambogan': (7.4478, 125.8078), 'La Filipina': (7.4478, 125.8078), 'Magugpo': (7.4478, 125.8078), 'Mankilam': (7.4478, 125.8078), 'Visayan Village': (7.4478, 125.8078), 'Molave Proper': (7.858, 123.424), 'Ipil Proper': (7.785, 122.586), 'Dapitan City Proper': (8.654, 123.424), 'Valencia City Proper': (7.9064, 125.095), 'Gingoog City Proper': (8.828, 125.102), 'Panabo City Proper': (7.3081, 125.684), 'Mati City Proper': (6.955, 126.216), 'Koronadal City Proper': (6.5, 124.846), 'Kidapawan City Proper': (7.008, 125.089), 'Tacurong City Proper': (6.692, 124.676), 'Molave Bus Terminal': (7.858, 123.424), 'Molave Van Terminal': (7.858, 123.424), 'Pagadian City Bus Terminal': (7.8257, 123.437), 'Pagadian City Van Terminal': (7.8257, 123.437), 'Ipil Bus Terminal': (7.785, 122.586), 'Ipil Van Terminal': (7.785, 122.586), 'Zamboanga City Bus Terminal': (6.9214, 122.079), 'Zamboanga City Van Terminal': (6.9214, 122.079), 'Dipolog City Bus Terminal': (8.588, 123.34), 'Dipolog City Van Terminal': (8.588, 123.34), 'Dapitan City Bus Terminal': (8.654, 123.424), 'Dapitan City Van Terminal': (8.654, 123.424), 'Iligan City Bus Terminal': (8.228, 124.245), 'Iligan City Van Terminal': (8.228, 124.245), 'Ozamiz City Bus Terminal': (8.148, 123.84), 'Ozamiz City Van Terminal': (8.148, 123.84), 'Cagayan de Oro City Bus Terminal': (8.4542, 124.6319), 'Cagayan de Oro City Van Terminal': (8.4542, 124.6319), 'Malaybalay City Bus Terminal': (8.1575, 125.1278), 'Malaybalay City Van Terminal': (8.1575, 125.1278), 'Valencia City Bus Terminal': (7.9064, 125.095), 'Valencia City Van Terminal': (7.9064, 125.095), 'Gingoog City Bus Terminal': (8.828, 125.102), 'Gingoog City Van Terminal': (8.828, 125.102), 'Butuan City Bus Terminal': (8.9475, 125.5406), 'Butuan City Van Terminal': (8.9475, 125.5406), 'Surigao City Bus Terminal': (9.789, 125.495), 'Surigao City Van Terminal': (9.789, 125.495), 'Davao City Bus Terminal': (7.0707, 125.6087), 'Davao City Van Terminal': (7.0707, 125.6087), 'Tagum City Bus Terminal': (7.4478, 125.8078), 'Tagum City Van Terminal': (7.4478, 125.8078), 'Panabo City Bus Terminal': (7.3081, 125.684), 'Panabo City Van Terminal': (7.3081, 125.684), 'Digos City Bus Terminal': (6.7497, 125.3572), 'Digos City Van Terminal': (6.7497, 125.3572), 'Mati City Bus Terminal': (6.955, 126.216), 'Mati City Van Terminal': (6.955, 126.216), 'General Santos City Bus Terminal': (6.1164, 125.1716), 'General Santos City Van Terminal': (6.1164, 125.1716), 'Koronadal City Bus Terminal': (6.5, 124.846), 'Koronadal City Van Terminal': (6.5, 124.846), 'Kidapawan City Bus Terminal': (7.008, 125.089), 'Kidapawan City Van Terminal': (7.008, 125.089), 'Tacurong City Bus Terminal': (6.692, 124.676), 'Tacurong City Van Terminal': (6.692, 124.676), 'Cotabato City Bus Terminal': (7.2236, 124.246), 'Cotabato City Van Terminal': (7.2236, 124.246)}

def get_location_coordinates(location):
    """Return coordinates for a known place, with a regional fallback."""
    if location in LOCATION_COORDINATES:
        return LOCATION_COORDINATES[location]

    fallback_centers = [
        ("Zamboanga", LOCATION_COORDINATES.get("Zamboanga City")),
        ("Pagadian", LOCATION_COORDINATES.get("Pagadian City")),
        ("Dipolog", LOCATION_COORDINATES.get("Dipolog City")),
        ("Dapitan", LOCATION_COORDINATES.get("Dapitan City")),
        ("Iligan", LOCATION_COORDINATES.get("Iligan City")),
        ("Ozamiz", LOCATION_COORDINATES.get("Ozamiz City")),
        ("Cagayan", LOCATION_COORDINATES.get("Cagayan de Oro City")),
        ("Bukidnon", LOCATION_COORDINATES.get("Malaybalay City")),
        ("Davao", LOCATION_COORDINATES.get("Davao City")),
        ("Tagum", LOCATION_COORDINATES.get("Tagum City")),
        ("Digos", LOCATION_COORDINATES.get("Digos City")),
        ("General", LOCATION_COORDINATES.get("General Santos City")),
        ("Koronadal", LOCATION_COORDINATES.get("Koronadal City")),
        ("Cotabato", LOCATION_COORDINATES.get("Cotabato City")),
        ("Butuan", LOCATION_COORDINATES.get("Butuan City")),
        ("Surigao", LOCATION_COORDINATES.get("Surigao City")),
        ("Tandag", LOCATION_COORDINATES.get("Tandag Airport")),
        ("San Francisco", (8.505, 125.978)),
        ("Agusan", (8.505, 125.978)),
        ("Bayugan", (8.745, 125.748)),
        ("Prosperidad", (8.598, 125.918)),
        ("Trento", (8.048, 126.063)),
    ]
    text = str(location)
    for keyword, coords in fallback_centers:
        if keyword.lower() in text.lower() and coords:
            return coords

    return None


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two coordinates in kilometers."""
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = (math.sin(dlat / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def calculate_distance_km(starting_location, destination):
    """Approximate straight-line distance between two known places."""
    a = get_location_coordinates(starting_location)
    b = get_location_coordinates(destination)
    if not a or not b:
        return None
    return haversine_km(a[0], a[1], b[0], b[1])

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def has_column(cursor, table_name, column_name):
    """True when the table already carries the given column."""
    return any(
        row["name"] == column_name
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    )


def add_missing_column(cursor, table_name, column_name, column_definition):
    """Safely add a column to an existing SQLite database."""
    if not has_column(cursor, table_name, column_name):
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN "
            f"{column_name} {column_definition}"
        )


def migrate_legacy_fare_columns(cursor):
    """
    Fold the old three-mode pricing (fare_type + fixed_fare + rate_per_km) into
    the single configurable engine, then drop the columns it replaced. Runs only
    on databases that still have them, so it is a no-op afterwards.
    """
    if not has_column(cursor, "vehicle_types", "fare_type"):
        return

    # A 'fixed' charter price becomes the base fare of a per-booking type;
    # 'distance' types charge every passenger, as they always did.
    cursor.execute(
        """
        UPDATE vehicle_types
        SET base_fare = CASE
                WHEN fare_type = 'fixed' AND base_fare = 0 THEN fixed_fare
                ELSE base_fare
            END,
            rate_per_km = CASE WHEN fare_type = 'fixed' THEN 0 ELSE rate_per_km END,
            included_distance = CASE WHEN fare_type = 'fixed' THEN 0 ELSE included_distance END,
            charge_basis = CASE WHEN fare_type = 'distance'
                                THEN 'per_passenger' ELSE 'per_booking' END,
            fare_configured = 1
        """
    )

    # The land/air/sea split used to live in a Python dict; give each type its own
    # value before that dict goes away.
    cursor.execute(
        """
        UPDATE vehicle_types
        SET location_type = CASE
                WHEN type_name IN ('Airplane', 'Plane') THEN 'air'
                WHEN type_name IN ('Ferry', 'Boat', 'Ship') THEN 'sea'
                ELSE 'land'
            END
        WHERE location_type IS NULL OR location_type = ''
        """
    )

    cursor.execute("ALTER TABLE vehicle_types DROP COLUMN fare_type")
    cursor.execute("ALTER TABLE vehicle_types DROP COLUMN fixed_fare")


def get_booking_type(vehicle):
    if vehicle in ("Bus", "Van"):
        return "Seat Reservation"
    if vehicle in ("Taxi", "Motor"):
        return "Ride Reservation"
    if vehicle in ("Airplane", "Ferry"):
        return "Ticket Reservation"
    return "Reservation"



def get_next_reservation_id(conn):
    """Return the next continuous reservation ID after the current highest ID."""
    row = conn.execute(
        "SELECT COALESCE(MAX(reservation_id), 0) + 1 AS next_id FROM reservations"
    ).fetchone()
    return int(row["next_id"])


def renumber_reservations_after_delete(conn, deleted_id):
    """
    Keep reservation IDs continuous after a deletion.

    Example: 1,2,3,4 -> delete 2 -> 1,2,3.
    Tickets belonging to shifted reservations are updated as well so their
    ticket numbers continue to match the reservation ID.
    """
    conn.execute(
        "DELETE FROM tickets WHERE reservation_id = ?",
        (deleted_id,)
    )

    conn.execute(
        "UPDATE tickets SET ticket_number = 'TMP-' || ticket_id "
        "WHERE reservation_id > ?",
        (deleted_id,)
    )
    conn.execute(
        "UPDATE tickets SET reservation_id = -reservation_id "
        "WHERE reservation_id > 0 AND reservation_id > ?",
        (deleted_id,)
    )
    conn.execute(
        "UPDATE reservations SET reservation_id = -reservation_id "
        "WHERE reservation_id > ?",
        (deleted_id,)
    )

    conn.execute(
        "UPDATE reservations SET reservation_id = -reservation_id - 1 "
        "WHERE reservation_id < 0"
    )
    conn.execute(
        "UPDATE tickets SET reservation_id = -reservation_id - 1 "
        "WHERE reservation_id < 0"
    )

    shifted_tickets = conn.execute(
        """
        SELECT ticket_id, reservation_id
        FROM tickets
        WHERE ticket_number LIKE 'TMP-%'
        ORDER BY reservation_id, ticket_id
        """
    ).fetchall()

    passenger_index = {}
    for ticket in shifted_tickets:
        reservation_id = int(ticket["reservation_id"])
        passenger_index[reservation_id] = passenger_index.get(reservation_id, 0) + 1
        new_ticket_number = create_ticket_number(
            reservation_id,
            passenger_index[reservation_id]
        )
        conn.execute(
            "UPDATE tickets SET ticket_number = ? WHERE ticket_id = ?",
            (new_ticket_number, ticket["ticket_id"])
        )

def create_ticket_number(reservation_id, passenger_index):
    """
    Ticket number is unique per passenger.
    Example: TRS-000001-01
    """
    return f"TRS-{reservation_id:06d}-{passenger_index:02d}"


def get_seat_list(vehicle, capacity=None):
    """
    Generates realistic seat/slot labels.

    Vehicle types the admin adds have no hand-written seat layout, so they fall
    back to one generic seat per allowed passenger.
    """
    if vehicle == "Bus":
        return [f"A{i}" for i in range(1, 46)]

    if vehicle == "Van":
        return [f"V{i}" for i in range(1, 13)]

    if vehicle == "Private Van":
        total = int(capacity) if capacity else 10
        return [f"PV{i}" for i in range(1, total + 1)]

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

    if capacity:
        return [f"S{i}" for i in range(1, int(capacity) + 1)]

    return []


def get_seat_capacity(conn, vehicle):
    """How many seats this vehicle type may sell, per the admin's setting."""
    row = conn.execute(
        "SELECT max_passengers FROM vehicle_types WHERE type_name = ?",
        (vehicle,)
    ).fetchone()
    return int(row["max_passengers"]) if row and row["max_passengers"] else 0


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
    available_seats = get_seat_list(vehicle, get_seat_capacity(conn, vehicle))

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
                round(float(reservation["fare"]) / max(1, number_of_passengers), 2),
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

    add_missing_column(cursor, "reservations", "passenger_names", "TEXT")
    add_missing_column(cursor, "reservations", "booking_reference", "TEXT")
    add_missing_column(cursor, "reservations", "vehicle_code", "TEXT")

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

    add_missing_column(cursor, "tickets", "ticket_number", "TEXT")
    add_missing_column(cursor, "tickets", "seat_number", "TEXT")
    add_missing_column(cursor, "tickets", "booking_type", "TEXT")
    add_missing_column(cursor, "tickets", "passengers", "INTEGER DEFAULT 1")
    add_missing_column(cursor, "tickets", "vehicle_code", "TEXT")

    cursor.execute(
        """
        UPDATE tickets
        SET booking_type = CASE
            WHEN vehicle IN ('Bus', 'Van', 'Private Van')
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

    # ── vehicle_types table ──────────────────────────────────────────────
    # Every row is priced by the same engine (see get_fare_breakdown):
    #   trip fare  = max(min_fare, base_fare + max(0, km - included_distance) * rate_per_km)
    #   total fare = trip fare x passengers (per_passenger) or once (per_booking),
    #                plus extra_charges
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_types (
            type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT UNIQUE NOT NULL,
            base_fare REAL NOT NULL DEFAULT 0,
            included_distance REAL NOT NULL DEFAULT 0,
            rate_per_km REAL NOT NULL DEFAULT 0,
            min_fare REAL NOT NULL DEFAULT 0,
            extra_charges REAL NOT NULL DEFAULT 0,
            extra_charges_label TEXT DEFAULT '',
            charge_basis TEXT NOT NULL DEFAULT 'per_booking',
            max_passengers INTEGER DEFAULT 45,
            location_type TEXT DEFAULT 'land',
            fare_configured INTEGER NOT NULL DEFAULT 0,
            is_available INTEGER DEFAULT 1
        )
        """
    )

    for column, definition in (
        ("base_fare", "REAL NOT NULL DEFAULT 0"),
        ("included_distance", "REAL NOT NULL DEFAULT 0"),
        ("min_fare", "REAL NOT NULL DEFAULT 0"),
        ("extra_charges", "REAL NOT NULL DEFAULT 0"),
        ("extra_charges_label", "TEXT DEFAULT ''"),
        ("charge_basis", "TEXT NOT NULL DEFAULT 'per_booking'"),
        ("location_type", "TEXT DEFAULT 'land'"),
        ("fare_configured", "INTEGER NOT NULL DEFAULT 0"),
    ):
        add_missing_column(cursor, "vehicle_types", column, definition)

    migrate_legacy_fare_columns(cursor)

    # Seed default vehicle types if empty
    existing_types = cursor.execute(
        "SELECT COUNT(*) FROM vehicle_types"
    ).fetchone()[0]
    if existing_types == 0:
        cursor.executemany(
            """
            INSERT OR IGNORE INTO vehicle_types
            (type_name, base_fare, included_distance, rate_per_km, min_fare,
             charge_basis, max_passengers, location_type, fare_configured, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
            """,
            [
                ("Bus",         0.0,    0.0,  2.22, 0.0, "per_passenger", 45, "land"),
                ("Van",         0.0,    0.0,  2.0,  0.0, "per_passenger", 12, "land"),
                ("Private Van", 1500.0, 25.0, 45.0, 0.0, "per_booking",   10, "land"),
                ("Taxi",        0.0,    0.0,  13.50, 0.0, "per_passenger",  4, "land"),
            ]
        )

    # ── vehicles table ───────────────────────────────────────────────────
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_code TEXT UNIQUE NOT NULL,
            vehicle_type TEXT NOT NULL,
            vehicle_name TEXT NOT NULL,
            plate_number TEXT,
            capacity INTEGER DEFAULT 1,
            status TEXT DEFAULT 'Available',
            assigned_driver TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )

    admin_password = hash_password("admin123")
    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (full_name, username, password, contact)
        VALUES (?, ?, ?, ?)
        """,
        ("System Administrator", "admin", admin_password, "Admin")
    )

    conn.commit()
    conn.close()

    ensure_tickets_for_old_reservations()


# ═══════════════════════════════════════════════════════════════════════
# NEW HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def generate_vehicle_code(conn):
    """
    Returns the next sequential vehicle code as a zero-padded 3-digit string
    (001, 002, …).  Never reuses codes from deleted vehicles.
    """
    row = conn.execute(
        "SELECT COALESCE(MAX(CAST(vehicle_code AS INTEGER)), 0) AS max_code FROM vehicles"
    ).fetchone()
    next_num = int(row["max_code"]) + 1
    return f"{next_num:03d}"


def generate_booking_reference(conn):
    """Returns a unique booking reference: BKF-YYYYMMDD-NNNN."""
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM reservations WHERE booking_reference LIKE ?",
        (f"BKF-{date_str}-%",)
    ).fetchone()
    seq = int(row["cnt"]) + 1
    return f"BKF-{date_str}-{seq:04d}"


class FareNotConfigured(ValueError):
    """A vehicle type has no admin-configured pricing yet."""


def get_vehicle_type(conn, type_name):
    return conn.execute(
        "SELECT * FROM vehicle_types WHERE type_name = ?", (type_name,)
    ).fetchone()


def get_fare_breakdown(conn, type_name, distance_km, passengers):
    """
    The pricing engine behind every vehicle type, driven entirely by that type's
    vehicle_types row:

        trip fare  = max(min_fare,
                         base_fare + max(0, km - included_distance) * rate_per_km)
        total fare = trip fare x passengers   (charge_basis = per_passenger)
                   = trip fare                (charge_basis = per_booking)
                   + extra_charges

    Returning the whole breakdown keeps the pre-booking estimate, the stored
    reservation, the ticket and the receipt showing the same numbers.
    """
    try:
        distance_km = max(0.0, float(distance_km or 0))
    except (TypeError, ValueError):
        distance_km = 0.0

    try:
        passengers = max(1, int(passengers or 1))
    except (TypeError, ValueError):
        passengers = 1

    row = get_vehicle_type(conn, type_name)
    if row is None:
        raise FareNotConfigured(f"'{type_name}' is not a vehicle type in the system.")
    if not row["fare_configured"]:
        raise FareNotConfigured(
            f"{type_name} has no fare configuration yet, so it cannot be priced. "
            "An admin must set its rates first."
        )

    base_fare = float(row["base_fare"] or 0)
    included_distance = float(row["included_distance"] or 0)
    rate_per_km = float(row["rate_per_km"] or 0)
    min_fare = float(row["min_fare"] or 0)
    extra_charges = float(row["extra_charges"] or 0)
    charge_basis = (
        row["charge_basis"]
        if row["charge_basis"] in CHARGE_BASES
        else "per_booking"
    )

    extra_distance = max(0.0, distance_km - included_distance)
    distance_charge = extra_distance * rate_per_km
    trip_fare = max(min_fare, base_fare + distance_charge)
    charged_times = passengers if charge_basis == "per_passenger" else 1

    return {
        "type_name": type_name,
        "charge_basis": charge_basis,
        "max_passengers": int(row["max_passengers"] or 1),
        "location_type": row["location_type"] or "land",
        "distance_km": round(distance_km, 2),
        "passengers": passengers,
        "base_fare": round(base_fare, 2),
        "included_distance": round(included_distance, 2),
        "extra_distance": round(extra_distance, 2),
        "rate_per_km": round(rate_per_km, 2),
        "distance_charge": round(distance_charge, 2),
        "min_fare": round(min_fare, 2),
        "minimum_fare_applied": min_fare > base_fare + distance_charge,
        "trip_fare": round(trip_fare, 2),
        "extra_charges": round(extra_charges, 2),
        "extra_charges_label": (row["extra_charges_label"] or "").strip(),
        "subtotal": round(trip_fare * charged_times, 2),
        "total_fare": round(trip_fare * charged_times + extra_charges, 2),
        "fare_per_passenger": round(
            (trip_fare * charged_times + extra_charges) / passengers, 2
        ),
    }


def fare_price_label(vt):
    """
    One-line description of how a type is priced, used by the vehicle pickers and
    the admin list so no template or script re-derives its own wording.
    """
    parts = []

    if vt["base_fare"]:
        text = f"₱{vt['base_fare']:,.2f} base"
        if vt["included_distance"]:
            text += f" (first {vt['included_distance']:g} km)"
        parts.append(text)

    if vt["rate_per_km"]:
        if vt["base_fare"] and vt["included_distance"]:
            parts.append(f"₱{vt['rate_per_km']:,.2f}/km after {vt['included_distance']:g} km")
        elif vt["included_distance"]:
            parts.append(f"₱{vt['rate_per_km']:,.2f}/km beyond {vt['included_distance']:g} km")
        else:
            parts.append(f"₱{vt['rate_per_km']:,.2f}/km")

    if vt["min_fare"]:
        parts.append(f"min ₱{vt['min_fare']:,.2f}")

    if vt["extra_charges"]:
        parts.append(
            f"+₱{vt['extra_charges']:,.2f} {vt['extra_charges_label'] or 'fees'}"
        )

    if not parts:
        return "Fare not configured"

    basis = "per passenger" if vt["charge_basis"] == "per_passenger" else "per booking"
    return " · ".join(parts) + f" · {basis}"


def get_vehicle_type_settings(conn):
    """
    Vehicle types as the booking forms need them: pricing, capacity and the
    land/air/sea location source, all straight from the database.
    """
    rows = conn.execute(
        "SELECT * FROM vehicle_types ORDER BY type_id"
    ).fetchall()
    settings = []
    for r in rows:
        vt = {
            "type_id": r["type_id"],
            "type_name": r["type_name"],
            "base_fare": float(r["base_fare"] or 0),
            "included_distance": float(r["included_distance"] or 0),
            "rate_per_km": float(r["rate_per_km"] or 0),
            "min_fare": float(r["min_fare"] or 0),
            "extra_charges": float(r["extra_charges"] or 0),
            "extra_charges_label": (r["extra_charges_label"] or "").strip(),
            "charge_basis": r["charge_basis"] or "per_booking",
            "max_passengers": int(r["max_passengers"] or 1),
            "location_type": r["location_type"] or "land",
            "fare_configured": bool(r["fare_configured"]),
            "is_available": r["is_available"],
            "booking_type": get_booking_type(r["type_name"]),
        }
        vt["bookable"] = vt["fare_configured"] and bool(vt["is_available"])
        vt["price_label"] = fare_price_label(vt)
        settings.append(vt)
    return settings


def fetch_osrm_route(pickup, destination):
    """
    Driving route between two (lat, lon) tuples from the public OSRM demo
    server, or None when the service is unreachable or finds no road.
    """
    lon1, lat1 = pickup[1], pickup[0]
    lon2, lat2 = destination[1], destination[0]
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TravelReservationSystem/1.0 (contact: local-app)"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError):
        return None

    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    route = data["routes"][0]
    return {
        "distance_km": route["distance"] / 1000.0,
        "duration_minutes": route["duration"] / 60.0,
        "geometry": route["geometry"],
    }


def read_coordinate(lat, lon):
    """A (lat, lon) tuple from submitted form values, or None if not usable."""
    try:
        point = (float(lat), float(lon))
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in point):
        return None
    if abs(point[0]) > 90 or abs(point[1]) > 180:
        return None
    return point


def resolve_trip_distance(submitted_km, pickup=None, destination=None,
                          starting_location="", destination_name=""):
    """
    The distance the server is willing to price a trip at.

    The browser measures the route for the estimate, but a booking is only
    trusted once it is measured here too: the map coordinates are re-routed, and
    when the route service is unavailable the submitted figure survives only if
    it is plausible next to the straight-line gap between the two points.
    """
    try:
        submitted_km = float(submitted_km or 0)
    except (TypeError, ValueError):
        submitted_km = 0.0

    straight_km = None
    if pickup and destination:
        straight_km = haversine_km(pickup[0], pickup[1], destination[0], destination[1])
        route = fetch_osrm_route(pickup, destination)
        if route:
            return round(min(route["distance_km"], MAX_TRIP_KM), 2)

    if straight_km is None:
        straight_km = calculate_distance_km(starting_location, destination_name)

    if submitted_km > 0:
        if straight_km:
            # Roads cannot beat a straight line, and rarely run three times longer.
            submitted_km = min(
                max(submitted_km, straight_km), straight_km * ROAD_FACTOR
            )
        return round(min(submitted_km, MAX_TRIP_KM), 2)

    return round(min(straight_km or 0.0, MAX_TRIP_KM), 2)


def get_available_vehicle_types(conn):
    """Returns all vehicle_types rows with live availability stats."""
    vehicle_stats = {}
    for r in conn.execute(
        """
        SELECT vehicle_type,
               COUNT(*) AS total,
               SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) AS available,
               SUM(CASE WHEN status IN ('Reserved','In Use') THEN 1 ELSE 0 END) AS reserved
        FROM vehicles
        WHERE is_active=1
        GROUP BY vehicle_type
        """
    ).fetchall():
        vehicle_stats[r["vehicle_type"]] = r

    settings = get_vehicle_type_settings(conn)
    for vt in settings:
        stats = vehicle_stats.get(vt["type_name"])
        vt["total_vehicles"] = int(stats["total"]) if stats else 0
        vt["available_vehicles"] = int(stats["available"] or 0) if stats else 0
        vt["reserved_vehicles"] = int(stats["reserved"] or 0) if stats else 0
    return settings


def assign_vehicle_to_reservation(conn, reservation_id):
    """
    On confirmation: assign the first available vehicle of the correct type
    to the reservation and mark it Reserved.
    Updates both the reservation and all its tickets.
    """
    r = conn.execute(
        "SELECT vehicle, vehicle_code FROM reservations WHERE reservation_id=?",
        (reservation_id,)
    ).fetchone()
    if not r:
        return
    if r["vehicle_code"]:
        return  # already assigned

    vehicle_row = conn.execute(
        "SELECT vehicle_id, vehicle_code FROM vehicles "
        "WHERE vehicle_type=? AND status='Available' AND is_active=1 "
        "ORDER BY vehicle_id LIMIT 1",
        (r["vehicle"],)
    ).fetchone()
    if not vehicle_row:
        return  # no vehicle available — admin can assign manually later

    code = vehicle_row["vehicle_code"]
    conn.execute(
        "UPDATE vehicles SET status='Reserved' WHERE vehicle_id=?",
        (vehicle_row["vehicle_id"],)
    )
    conn.execute(
        "UPDATE reservations SET vehicle_code=? WHERE reservation_id=?",
        (code, reservation_id)
    )
    conn.execute(
        "UPDATE tickets SET vehicle_code=? WHERE reservation_id=?",
        (code, reservation_id)
    )


def release_vehicle_from_reservation(conn, reservation_id):
    """
    On cancellation/completion: release the vehicle back to Available.
    """
    r = conn.execute(
        "SELECT vehicle_code FROM reservations WHERE reservation_id=?",
        (reservation_id,)
    ).fetchone()
    if not r or not r["vehicle_code"]:
        return
    conn.execute(
        "UPDATE vehicles SET status='Available' WHERE vehicle_code=? AND status='Reserved'",
        (r["vehicle_code"],)
    )


# ═══════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════

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


@app.route("/api/search-address")
def api_search_address():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"ok": False, "error": "Type at least 2 characters."})

    results = []
    seen_names = set()
    q_lower = query.lower()

    # Priority 1: Match local database locations and barangays
    for city, barangays in BARANGAYS_BY_CITY.items():
        coords_city = LOCATION_COORDINATES.get(city)
        if q_lower in city.lower() and city not in seen_names and coords_city:
            results.append({"name": f"{city}, Mindanao", "lat": coords_city[0], "lon": coords_city[1]})
            seen_names.add(city)
        for brgy in barangays:
            full_brgy_name = f"{brgy}, {city}"
            if (q_lower in brgy.lower() or q_lower in full_brgy_name.lower()) and full_brgy_name not in seen_names:
                coords = LOCATION_COORDINATES.get(brgy) or coords_city
                if coords:
                    results.append({"name": full_brgy_name, "lat": coords[0], "lon": coords[1]})
                    seen_names.add(full_brgy_name)
            if len(results) >= 8:
                break
        if len(results) >= 8:
            break

    # Priority 2: Online OpenStreetMap search if fewer than 5 results
    if len(results) < 5:
        try:
            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
                "q": query, "format": "jsonv2", "limit": 6, "addressdetails": 1, "countrycodes": "ph"
            })
            req = urllib.request.Request(url, headers={"User-Agent": "TravelReservationSystem/1.0 (contact: local-app)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for item in data:
                dname = item.get("display_name", query)
                if dname not in seen_names:
                    results.append({"name": dname, "lat": float(item["lat"]), "lon": float(item["lon"])})
                    seen_names.add(dname)
        except Exception:
            pass

    return jsonify({"ok": True, "results": results[:10]})


@app.route("/api/calculate-route")
def api_calculate_route():
    """Route + fare estimate for the booking form. Nothing here is saved."""
    try:
        lat1 = float(request.args.get("lat1"))
        lon1 = float(request.args.get("lon1"))
        lat2 = float(request.args.get("lat2"))
        lon2 = float(request.args.get("lon2"))
        vehicle = request.args.get("vehicle", "").strip()
        passengers = max(1, int(request.args.get("passengers", 1)))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid route or vehicle request."})

    route = fetch_osrm_route((lat1, lon1), (lat2, lon2))
    if not route:
        return jsonify({"ok": False, "error": "No road route found."})

    distance_km = min(route["distance_km"], MAX_TRIP_KM)

    conn = get_db()
    try:
        breakdown = get_fare_breakdown(conn, vehicle, distance_km, passengers)
    except FareNotConfigured as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    finally:
        conn.close()

    return jsonify({
        "ok": True,
        "distance_km": round(distance_km, 2),
        "duration_minutes": round(route["duration_minutes"], 1),
        "geometry": route["geometry"],
        "vehicle": vehicle,
        "passengers": passengers,
        "fare": breakdown,
        "fare_per_passenger": breakdown["fare_per_passenger"],
        "total_fare": breakdown["total_fare"],
    })


@app.route("/api/calculate-fare")
def api_calculate_fare():
    """Fare estimate for a distance the form already has."""
    vehicle = request.args.get("vehicle", "").strip()
    if not vehicle:
        return jsonify({"ok": False, "error": "Vehicle required."})
    try:
        distance_km = float(request.args.get("distance", 0))
        passengers = max(1, int(request.args.get("passengers", 1)))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid distance or passenger count."})

    conn = get_db()
    try:
        breakdown = get_fare_breakdown(conn, vehicle, distance_km, passengers)
    except FareNotConfigured as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    finally:
        conn.close()

    return jsonify({
        "ok": True,
        "fare": breakdown["total_fare"],
        "rate_per_km": breakdown["rate_per_km"],
        "breakdown": breakdown,
        "max_passengers": breakdown["max_passengers"],
    })


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
                old_name = request.form.get("passenger_name", "").strip()
                if old_name:
                    passenger_names = [old_name]

            contact = request.form["contact"].strip()
            starting_location = request.form["starting_location"].strip()
            origin = request.form.get("origin", "").strip()
            destination = request.form["destination"].strip()
            travel_date = request.form["travel_date"]
            travel_time = request.form["travel_time"]
            vehicle = request.form["vehicle"].strip()
            passengers = int(request.form["passengers"])

            submitted_distance = request.form.get("distance", "").strip()
            pickup_coord = read_coordinate(
                request.form.get("pickup_lat"), request.form.get("pickup_lon"))
            destination_coord = read_coordinate(
                request.form.get("destination_lat"),
                request.form.get("destination_lon"))

        except (KeyError, ValueError):
            flash("Please complete all reservation fields correctly.", "error")
            return redirect(url_for("reservation"))

        if not passenger_names:
            flash("Please enter at least one passenger name.", "error")
            return redirect(url_for("reservation"))

        if len(passenger_names) != passengers:
            flash("The number of passenger names must match the number of passengers.", "error")
            return redirect(url_for("reservation"))

        passenger_name = passenger_names[0]

        if not contact:
            flash("Contact number is required.", "error")
            return redirect(url_for("reservation"))

        conn = get_db()
        vt_row = get_vehicle_type(conn, vehicle)
        conn.close()

        if not vt_row or not vt_row["is_available"]:
            flash("Invalid or unavailable vehicle selected.", "error")
            return redirect(url_for("reservation"))

        if not vt_row["fare_configured"]:
            flash(
                f"{vehicle} cannot be booked yet: an admin has to set its fare first.",
                "error"
            )
            return redirect(url_for("reservation"))

        max_passengers_allowed = int(vt_row["max_passengers"] or 1)

        if not starting_location or not destination:
            flash("Please complete the location fields.", "error")
            return redirect(url_for("reservation"))

        if not origin:
            origin = starting_location

        # The browser's figure is only a hint; the server measures the trip itself.
        distance = resolve_trip_distance(
            submitted_distance, pickup_coord, destination_coord,
            starting_location, origin
        )

        if distance <= 0:
            flash(
                "Distance could not be calculated. Please choose the pickup "
                "and destination on the map.",
                "error"
            )
            return redirect(url_for("reservation"))

        if passengers < 1:
            flash("Passenger count must be at least 1.", "error")
            return redirect(url_for("reservation"))

        if passengers > max_passengers_allowed:
            flash(f"{vehicle} can only accommodate {max_passengers_allowed} passenger(s) per booking.", "error")
            return redirect(url_for("reservation"))

        # The fare is computed here, from the database, and never taken from the form.
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE")

            breakdown = get_fare_breakdown(conn, vehicle, distance, passengers)
            fare = breakdown["total_fare"]

            booking_reference = generate_booking_reference(conn)
            reservation_id = get_next_reservation_id(conn)

            conn.execute(
                """
                INSERT INTO reservations (
                    reservation_id, user_id, passenger_name, passenger_names,
                    contact, starting_location, origin, destination,
                    travel_date, travel_time, vehicle, passengers,
                    distance, fare, status, booking_reference
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reservation_id, session["user_id"], passenger_name,
                    json.dumps(passenger_names, ensure_ascii=False),
                    contact, starting_location, origin, destination,
                    travel_date, travel_time, vehicle, passengers,
                    distance, fare, "Pending", booking_reference
                )
            )

            reservation_row = conn.execute(
                "SELECT * FROM reservations WHERE reservation_id=?",
                (reservation_id,)
            ).fetchone()

            assign_seats(conn, reservation_row, passengers)
            create_tickets_for_reservation(conn, reservation_id)
            conn.commit()

        except ValueError as error:
            conn.rollback()
            conn.close()
            flash(str(error), "error")
            return redirect(url_for("reservation"))

        except sqlite3.Error as error:
            conn.rollback()
            conn.close()
            flash(f"Reservation could not be saved: {error}", "error")
            return redirect(url_for("reservation"))

        conn.close()

        flash(
            f"Reservation submitted! Booking Ref: {booking_reference}. "
            f"{passengers} ticket(s) created. Awaiting admin confirmation.",
            "success"
        )
        return redirect(url_for("dashboard"))

    # GET — the vehicle picker is built entirely from configured, available types
    conn = get_db()
    db_vehicle_types = [
        vt for vt in get_available_vehicle_types(conn) if vt["bookable"]
    ]
    conn.close()

    return render_template(
        "reservation.html",
        db_vehicle_types=db_vehicle_types,
        land_locations=LAND_LOCATIONS,
        airport_locations=AIRPORT_LOCATIONS,
        port_locations=PORT_LOCATIONS,
        vehicle_location_types={
            vt["type_name"]: vt["location_type"] for vt in db_vehicle_types
        },
        location_coordinates=LOCATION_COORDINATES,
        barangays_by_city=BARANGAYS_BY_CITY,
        terminals_by_city=TERMINALS_BY_CITY
    )


@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("username") != "admin":
        flash("Admin access only.", "error")
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
        JOIN users u ON r.user_id = u.user_id
        ORDER BY r.reservation_id DESC
        """
    ).fetchall()

    tickets = conn.execute(
        """
        SELECT t.*, u.full_name AS account_name, u.username
        FROM tickets t
        JOIN users u ON t.user_id = u.user_id
        ORDER BY t.ticket_id DESC
        """
    ).fetchall()

    users = conn.execute(
        "SELECT user_id, full_name, username, contact FROM users ORDER BY user_id DESC"
    ).fetchall()

    vehicles = conn.execute(
        "SELECT * FROM vehicles WHERE is_active=1 ORDER BY vehicle_code"
    ).fetchall()

    vehicle_type_stats = get_available_vehicle_types(conn)

    # Summary stats
    total_res = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    pending_res = conn.execute("SELECT COUNT(*) FROM reservations WHERE status='Pending'").fetchone()[0]
    confirmed_res = conn.execute("SELECT COUNT(*) FROM reservations WHERE status='Confirmed'").fetchone()[0]
    total_vehicles = conn.execute("SELECT COUNT(*) FROM vehicles WHERE is_active=1").fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        reservations=reservations,
        tickets=tickets,
        users=users,
        vehicles=vehicles,
        vehicle_type_stats=vehicle_type_stats,
        total_res=total_res,
        pending_res=pending_res,
        confirmed_res=confirmed_res,
        total_vehicles=total_vehicles
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
            "UPDATE reservations SET status=? WHERE reservation_id=?",
            (new_status, reservation_id)
        )
        conn.execute(
            "UPDATE tickets SET status=? WHERE reservation_id=?",
            (new_status, reservation_id)
        )

        # On confirmation: try to assign a vehicle
        if new_status == "Confirmed":
            assign_vehicle_to_reservation(conn, reservation_id)

        # On cancellation or completion: release the vehicle
        if new_status in ("Cancelled", "Completed"):
            release_vehicle_from_reservation(conn, reservation_id)
            if new_status == "Completed":
                # Mark vehicle as Available again after trip completion
                r = conn.execute(
                    "SELECT vehicle_code FROM reservations WHERE reservation_id=?",
                    (reservation_id,)
                ).fetchone()
                if r and r["vehicle_code"]:
                    conn.execute(
                        "UPDATE vehicles SET status='Available' WHERE vehicle_code=?",
                        (r["vehicle_code"],)
                    )

        conn.commit()

    except sqlite3.Error as error:
        conn.rollback()
        conn.close()
        flash(f"Status update failed: {error}", "error")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    flash(f"Reservation #{reservation_id} status updated to {new_status}.", "success")
    return redirect(url_for("admin_dashboard"))


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
            vehicle = request.form["vehicle"].strip()
            passengers = int(request.form["passengers"])
            submitted_distance = request.form.get("distance", "").strip()
            pickup_coord = read_coordinate(
                request.form.get("pickup_lat"), request.form.get("pickup_lon"))
            destination_coord = read_coordinate(
                request.form.get("destination_lat"),
                request.form.get("destination_lon"))
        except (KeyError, ValueError):
            flash("Please complete all reservation fields correctly.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        if not passenger_names or len(passenger_names) != passengers:
            flash("The number of passenger names must match the number of passengers.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        if not contact or not starting_location or not origin or not destination:
            flash("Please complete all required fields.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))
        conn = get_db()
        vt_row = get_vehicle_type(conn, vehicle)

        if not vt_row or not vt_row["is_available"]:
            conn.close()
            flash("Invalid or unavailable vehicle selected.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        if not vt_row["fare_configured"]:
            conn.close()
            flash(
                f"{vehicle} cannot be booked yet: an admin has to set its fare first.",
                "error"
            )
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        max_passengers_allowed = int(vt_row["max_passengers"] or 1)

        if passengers < 1 or passengers > max_passengers_allowed:
            conn.close()
            flash(f"{vehicle} can only accommodate {max_passengers_allowed} passenger(s) per booking.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        # Re-measure the trip only when the customer actually moved it; otherwise
        # keep the distance they were originally quoted.
        if (starting_location == reservation_row["starting_location"]
                and origin == reservation_row["origin"]
                and destination == reservation_row["destination"]):
            distance = float(reservation_row["distance"] or 0)
        else:
            distance = resolve_trip_distance(
                submitted_distance, pickup_coord, destination_coord,
                starting_location, origin
            )

        if distance <= 0:
            conn.close()
            flash("Distance could not be calculated for the selected locations.", "error")
            return redirect(url_for("edit_reservation", reservation_id=reservation_id))

        fare = get_fare_breakdown(conn, vehicle, distance, passengers)["total_fare"]

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

    conn = get_db()
    bookable_types = [
        vt for vt in get_available_vehicle_types(conn) if vt["bookable"]
    ]
    conn.close()

    # A booking whose type has since been disabled or un-configured must stay
    # editable, so keep that row in the list.
    if all(vt["type_name"] != reservation_row["vehicle"] for vt in bookable_types):
        conn = get_db()
        current = next(
            (vt for vt in get_vehicle_type_settings(conn)
             if vt["type_name"] == reservation_row["vehicle"]), None
        )
        conn.close()
        if current:
            bookable_types.append(current)

    return render_template(
        "edit_reservation.html",
        reservation=reservation_row,
        passenger_names=saved_names,
        db_vehicle_types=bookable_types,
        land_locations=LAND_LOCATIONS,
        airport_locations=AIRPORT_LOCATIONS,
        port_locations=PORT_LOCATIONS,
        vehicle_location_types={
            vt["type_name"]: vt["location_type"] for vt in bookable_types
        },
        location_coordinates=LOCATION_COORDINATES,
        barangays_by_city=BARANGAYS_BY_CITY,
        terminals_by_city=TERMINALS_BY_CITY
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

        conn.execute(
            "DELETE FROM reservations WHERE reservation_id = ? AND user_id = ?",
            (reservation_id, session["user_id"])
        )
        renumber_reservations_after_delete(conn, reservation_id)
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

        conn.execute("DELETE FROM reservations WHERE reservation_id = ?", (reservation_id,))
        renumber_reservations_after_delete(conn, reservation_id)
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

    if not ticket:
        conn.close()
        abort(404)

    if "user_id" not in session:
        conn.close()
        return redirect(url_for("login"))

    if session.get("username") != "admin":
        if ticket["user_id"] != session.get("user_id"):
            conn.close()
            flash(
                "You can only view your own ticket.",
                "error"
            )
            return redirect(url_for("dashboard"))

    # Also fetch the reservation for booking_reference
    reservation = conn.execute(
        "SELECT * FROM reservations WHERE reservation_id=?",
        (ticket["reservation_id"],)
    ).fetchone()

    conn.close()

    qr_data_uri, verification_url = make_qr_data_uri(
        ticket["ticket_number"]
    )

    return render_template(
        "ticket.html",
        ticket=ticket,
        reservation=reservation,
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
            r.fare AS reservation_fare,
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
            t.ticket_id,
            t.ticket_number,
            t.reservation_id,
            t.passenger_name,
            t.contact,
            t.starting_location,
            t.origin,
            t.destination,
            t.travel_date,
            t.travel_time,
            t.vehicle,
            t.seat_number,
            t.fare,
            t.status,
            t.vehicle_code,
            t.passengers,
            r.booking_reference
        FROM tickets t
        LEFT JOIN reservations r ON t.reservation_id = r.reservation_id
        WHERE t.ticket_number = ?
        """,
        (ticket_number,)
    ).fetchone()

    conn.close()

    response = make_response_with_no_cache(
        render_template(
            "verify.html",
            ticket=ticket,
            ticket_number=ticket_number
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


# ═══════════════════════════════════════════════════════════════════════
# ADMIN — VEHICLE TYPE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

FARE_AMOUNT_FIELDS = (
    "base_fare", "included_distance", "rate_per_km", "min_fare", "extra_charges"
)

FARE_FIELD_NAMES = {
    "base_fare": "Base fare",
    "included_distance": "Included distance",
    "rate_per_km": "Rate per kilometer",
    "min_fare": "Minimum fare",
    "extra_charges": "Additional charges",
}


def read_fare_form(form):
    """
    Read and validate the pricing fields of the vehicle-type form.

    Every fare column is stored as a non-negative number, and a type only counts
    as configured once the admin has actually set something to charge, so an
    unpriced type can never quietly book at ₱0.
    """
    values = {}
    for name in FARE_AMOUNT_FIELDS:
        raw = str(form.get(name, "") or "").strip()
        try:
            amount = float(raw) if raw else 0.0
        except ValueError:
            raise ValueError(f"{FARE_FIELD_NAMES[name]} must be a number.")
        if amount < 0:
            raise ValueError(f"{FARE_FIELD_NAMES[name]} cannot be negative.")
        values[name] = round(amount, 2)

    charge_basis = form.get("charge_basis", "per_booking")
    if charge_basis not in CHARGE_BASES:
        raise ValueError("Choose how the fare is charged: per passenger or per booking.")

    location_type = form.get("location_type", "land")
    if location_type not in LOCATION_TYPES:
        raise ValueError("Location type must be land, air or sea.")

    try:
        max_passengers = int(form.get("max_passengers", 0))
    except ValueError:
        raise ValueError("Maximum passengers must be a whole number.")
    if not 1 <= max_passengers <= 500:
        raise ValueError("Maximum passengers must be between 1 and 500.")

    if not any(values[name] for name in
               ("base_fare", "rate_per_km", "min_fare", "extra_charges")):
        raise ValueError(
            "Set at least one charge — a base fare, a per-kilometre rate, a "
            "minimum fare or additional fees — before saving this vehicle type."
        )

    values.update(
        charge_basis=charge_basis,
        location_type=location_type,
        max_passengers=max_passengers,
        extra_charges_label=str(form.get("extra_charges_label", "")).strip()[:60],
    )
    return values


@app.route("/admin/vehicle-types")
def admin_vehicle_types():
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    types = get_available_vehicle_types(conn)
    conn.close()
    return render_template("admin_vehicle_types.html", vehicle_type_stats=types)


@app.route("/admin/vehicle-types/new", methods=["GET", "POST"])
def admin_add_vehicle_type():
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))

    form_values = request.form if request.method == "POST" else None

    if request.method == "POST":
        type_name = (form_values.get("type_name") or "").strip()
        if not type_name:
            flash("Vehicle type name is required.", "error")
            return render_template(
                "admin_vehicle_type_form.html", vt=None, form_values=form_values,
                mode="add"
            )
        try:
            values = read_fare_form(form_values)
        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "admin_vehicle_type_form.html", vt=None, form_values=form_values,
                mode="add"
            )

        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO vehicle_types
                (type_name, base_fare, included_distance, rate_per_km, min_fare,
                 extra_charges, extra_charges_label, charge_basis, max_passengers,
                 location_type, fare_configured, is_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (type_name, values["base_fare"], values["included_distance"],
                 values["rate_per_km"], values["min_fare"], values["extra_charges"],
                 values["extra_charges_label"], values["charge_basis"],
                 values["max_passengers"], values["location_type"],
                 1 if form_values.get("is_available") else 0)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash(f"A vehicle type named '{type_name}' already exists.", "error")
            return render_template(
                "admin_vehicle_type_form.html", vt=None, form_values=form_values,
                mode="add"
            )
        conn.close()
        flash(f"{type_name} added and priced. It is now bookable.", "success")
        return redirect(url_for("admin_vehicle_types"))

    return render_template("admin_vehicle_type_form.html", vt=None,
                           form_values=None, mode="add")


@app.route("/admin/vehicle-types/edit/<int:type_id>", methods=["GET", "POST"])
def admin_edit_vehicle_type(type_id):
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    vt = conn.execute("SELECT * FROM vehicle_types WHERE type_id=?", (type_id,)).fetchone()
    if not vt:
        conn.close()
        abort(404)
    if request.method == "POST":
        try:
            values = read_fare_form(request.form)
            conn.execute(
                """
                UPDATE vehicle_types
                SET base_fare=?, included_distance=?, rate_per_km=?, min_fare=?,
                    extra_charges=?, extra_charges_label=?, charge_basis=?,
                    max_passengers=?, location_type=?, fare_configured=1
                WHERE type_id=?
                """,
                (values["base_fare"], values["included_distance"],
                 values["rate_per_km"], values["min_fare"], values["extra_charges"],
                 values["extra_charges_label"], values["charge_basis"],
                 values["max_passengers"], values["location_type"], type_id)
            )
            conn.commit()
            conn.close()
            flash(
                f"Pricing for '{vt['type_name']}' updated. Existing bookings keep "
                "the fare they were quoted.",
                "success"
            )
            return redirect(url_for("admin_vehicle_types"))
        except (ValueError, sqlite3.Error) as e:
            conn.close()
            flash(f"Update failed: {e}", "error")
            return redirect(url_for("admin_edit_vehicle_type", type_id=type_id))
    settings = get_vehicle_type_settings(conn)
    conn.close()
    current = next(s for s in settings if s["type_id"] == type_id)
    return render_template("admin_vehicle_type_form.html", vt=current,
                           form_values=None, mode="edit")


@app.route("/admin/vehicle-types/toggle/<int:type_id>", methods=["POST"])
def admin_toggle_vehicle_type(type_id):
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    vt = conn.execute(
        "SELECT type_name, is_available, fare_configured FROM vehicle_types WHERE type_id=?",
        (type_id,)
    ).fetchone()
    if not vt:
        conn.close()
        abort(404)
    if not vt["is_available"] and not vt["fare_configured"]:
        conn.close()
        flash(
            f"Set the fare for {vt['type_name']} before making it bookable.",
            "error"
        )
        return redirect(url_for("admin_edit_vehicle_type", type_id=type_id))
    new_val = 0 if vt["is_available"] else 1
    conn.execute("UPDATE vehicle_types SET is_available=? WHERE type_id=?", (new_val, type_id))
    conn.commit()
    conn.close()
    state = "enabled" if new_val else "disabled"
    flash(f"{vt['type_name']} availability {state}.", "success")
    return redirect(url_for("admin_vehicle_types"))


# ═══════════════════════════════════════════════════════════════════════
# ADMIN — VEHICLE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@app.route("/admin/vehicles")
def admin_vehicles():
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    vehicles = conn.execute(
        "SELECT * FROM vehicles WHERE is_active=1 ORDER BY vehicle_code"
    ).fetchall()
    vehicle_type_stats = get_available_vehicle_types(conn)
    conn.close()
    return render_template("admin_vehicles.html", vehicles=vehicles, vehicle_type_stats=vehicle_type_stats)


@app.route("/admin/vehicles/add", methods=["GET", "POST"])
def admin_add_vehicle():
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    vehicle_types = conn.execute("SELECT type_name FROM vehicle_types ORDER BY type_id").fetchall()
    if request.method == "POST":
        try:
            vehicle_type = request.form["vehicle_type"].strip()
            vehicle_name = request.form["vehicle_name"].strip()
            plate_number = request.form.get("plate_number", "").strip()
            capacity = int(request.form.get("capacity", 1))
            assigned_driver = request.form.get("assigned_driver", "").strip()
            status = request.form.get("status", "Available")
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not vehicle_type or not vehicle_name:
                flash("Vehicle type and name are required.", "error")
                return render_template("admin_vehicle_form.html", vehicle_types=vehicle_types, mode="add")

            conn.execute("BEGIN IMMEDIATE")
            vehicle_code = generate_vehicle_code(conn)
            conn.execute(
                """
                INSERT INTO vehicles
                (vehicle_code, vehicle_type, vehicle_name, plate_number,
                 capacity, status, assigned_driver, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (vehicle_code, vehicle_type, vehicle_name, plate_number,
                 capacity, status, assigned_driver, now_str)
            )
            conn.commit()
            conn.close()
            flash(f"Vehicle registered with code {vehicle_code}.", "success")
            return redirect(url_for("admin_vehicles"))
        except sqlite3.IntegrityError:
            conn.rollback()
            conn.close()
            flash("Plate number already exists.", "error")
            return redirect(url_for("admin_add_vehicle"))
        except (ValueError, sqlite3.Error) as e:
            conn.rollback()
            conn.close()
            flash(f"Failed to add vehicle: {e}", "error")
            return redirect(url_for("admin_add_vehicle"))
    conn.close()
    return render_template("admin_vehicle_form.html", vehicle_types=vehicle_types, mode="add")


@app.route("/admin/vehicles/edit/<int:vehicle_id>", methods=["GET", "POST"])
def admin_edit_vehicle(vehicle_id):
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    vehicle = conn.execute(
        "SELECT * FROM vehicles WHERE vehicle_id=? AND is_active=1", (vehicle_id,)
    ).fetchone()
    if not vehicle:
        conn.close()
        abort(404)
    vehicle_types = conn.execute("SELECT type_name FROM vehicle_types ORDER BY type_id").fetchall()
    if request.method == "POST":
        try:
            vehicle_type = request.form["vehicle_type"].strip()
            vehicle_name = request.form["vehicle_name"].strip()
            plate_number = request.form.get("plate_number", "").strip()
            capacity = int(request.form.get("capacity", 1))
            assigned_driver = request.form.get("assigned_driver", "").strip()
            status = request.form.get("status", "Available")
            conn.execute(
                """
                UPDATE vehicles
                SET vehicle_type=?, vehicle_name=?, plate_number=?,
                    capacity=?, status=?, assigned_driver=?
                WHERE vehicle_id=?
                """,
                (vehicle_type, vehicle_name, plate_number,
                 capacity, status, assigned_driver, vehicle_id)
            )
            conn.commit()
            conn.close()
            flash(f"Vehicle {vehicle['vehicle_code']} updated.", "success")
            return redirect(url_for("admin_vehicles"))
        except (ValueError, sqlite3.Error) as e:
            conn.rollback()
            conn.close()
            flash(f"Failed to update vehicle: {e}", "error")
            return redirect(url_for("admin_edit_vehicle", vehicle_id=vehicle_id))
    conn.close()
    return render_template("admin_vehicle_form.html", vehicle=vehicle, vehicle_types=vehicle_types, mode="edit")


@app.route("/admin/vehicles/delete/<int:vehicle_id>", methods=["POST"])
def admin_delete_vehicle(vehicle_id):
    if "user_id" not in session or session.get("username") != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("UPDATE vehicles SET is_active=0 WHERE vehicle_id=?", (vehicle_id,))
    conn.commit()
    conn.close()
    flash("Vehicle removed from the registry.", "success")
    return redirect(url_for("admin_vehicles"))


# Runs on import so schema migrations also apply when launched with `flask run`,
# not only via `python app.py`.
init_database()


if __name__ == "__main__":

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
