from flask import Flask, Response, request
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# WGS84 (GPS) -> EOV (Magyar Egységes Országos Vetület) konverter
# Az 'always_xy=True' miatt a sorrend: (lon, lat) -> (East, North)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Kiszámolja a csempe bal felső sarkának WGS84 (GPS) koordinátáit"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

# A te kérésed szerinti útvonal: /api/z/x/y.png
@app.route('/api/<int:z>/<int:x>/<int:y>.png')
def mepar_proxy(z, x, y):
    try:
        # 1. GPS koordináta számítás a csempe adatokból
        lat, lon = get_tile_bounds(z, x, y)
        
        # 2. Átváltás EOV-ra (EOV Kelet, EOV Észak)
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 3. BBOX számítás az adott zoom szinthez (Méter alapú ablak)
        res = 156543.03 / (2**z) 
        size = res * 256
        
        # MEPAR BBOX (minX, minY, maxX, maxY)
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. MEPAR WMS URL (2023-as légi fotó rétegek)
        # Fontos: A MEPAR szervere EPSG:23700-at (EOV) vár
        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        # 5. Fejlécek (Böngésző emuláció curl_cffi-vel)
        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Lekérés curl_cffi-vel (Chrome impersonate a TLS ujjlenyomat miatt)
        r = requests.get(mepar_url, headers=headers, impersonate="chrome110", timeout=15)
        
        if r.status_code == 200:
            return Response(r.content, mimetype='image/png')
        else:
            return f"MEPAR hiba: {r.status_code}", 502

    except Exception as e:
        # Hiba esetén kiírjuk a logba
        print(f"HIBA: {str(e)}")
        return f"Szerver hiba: {str(e)}", 500

@app.route('/')
def home():
    return "MEPAR Proxy fut! Probald: /api/14/8950/5670.png"

# Vercel-nek kell az app objektum
app = app
