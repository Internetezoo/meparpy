from flask import Flask, Response, request
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# WGS84 (GPS) -> EOV (Magyar Egységes Országos Vetület) konverter
# always_xy=True: (lon, lat) sorrendet vár és (East, North) sorrendet ad vissza
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Kiszámolja a csempe bal felső sarkának GPS koordinátáit"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/api/tile/<int:z>/<int:x>/<int:y>.png')
def mepar_proxy(z, x, y):
    try:
        # 1. GPS koordináta kiszámítása a Locus csempeadataiból
        lat, lon = get_tile_bounds(z, x, y)
        
        # 2. Átváltás EOV-ra (ez kell a MEPAR szerverének)
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 3. Méretarány meghatározása a BBOX-hoz
        # Web Mercator közelítés: 0. zoomon 156543 méter/pixel
        res = 156543.03 / (2**z)
        size = res * 256 # Egy 256x256-os csempe valós mérete méterben
        
        # MEPAR BBOX összeállítása: minX, minY, maxX, maxY
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. MEPAR WMS lekérő URL (2023-as légi fotó rétegekkel)
        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        # 5. Fejlécek a tiltás elkerülésére
        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Lekérés a curl_cffi segítségével (Chrome ujjlenyomat emulálása)
        r = requests.get(mepar_url, headers=headers, impersonate="chrome110", timeout=15)
        
        if r.status_code == 200:
            return Response(r.content, mimetype='image/png')
        else:
            return f"MEPAR hiba: {r.status_code}", 502

    except Exception as e:
        print(f"Hiba: {str(e)}")
        return f"Szerver hiba: {str(e)}", 500

# Kezdőoldal, hogy tudd, él a szerver
@app.route('/')
def home():
    return "MEPAR Proxy online. Minta: /api/tile/14/8950/5670.png"

# Vercelnek szüksége lehet erre az exportra
app = app
