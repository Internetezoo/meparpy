from flask import Flask, Response
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# GPS -> EOV
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

# 1. TESZT ÚTVONAL - Csak a Parlament (fixen)
@app.route('/test-parlament')
def test_parlament():
    # Fixen a Parlament (z=14, x=8652, y=5836)
    return proxy(14, 8652, 5836)

# 2. VALÓDI ÚTVONAL - Amit a Locus hív
@app.route('/<int:z>/<int:x>/<int:y>.png')
@app.route('/api/<int:z>/<int:x>/<int:y>.png')
def proxy(z, x, y):
    try:
        lat, lon = get_tile_bounds(z, x, y)
        eov_x, eov_y = transformer.transform(lon, lat)
        
        res = 156543.03392804097 / (2**z)
        size = res * 256
        
        # BBOX: minX, minY, maxX, maxY
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
        }

        r = requests.get(mepar_url, headers=headers, impersonate="chrome124", timeout=15)
        return Response(r.content, mimetype='image/png')
    except Exception as e:
        return f"Hiba tortent: {str(e)}", 500

@app.route('/')
def home():
    return "Proxy fut! Probald: /test-parlament"

app = app
