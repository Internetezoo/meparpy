from flask import Flask, Response
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# GPS (4326) -> EOV (23700)
# Az always_xy=True KÖTELEZŐ, hogy a lon->X (Kelet) és lat->Y (Észak) legyen!
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Web Mercator (Google/Locus) csempe sarokpont GPS koordinátái"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/<int:z>/<int:x>/<int:y>.png')
@app.route('/api/<int:z>/<int:x>/<int:y>.png')
def proxy(z, x, y):
    try:
        # 1. GPS koordináta kiszámítása
        lat, lon = get_tile_bounds(z, x, y)
        
        # 2. Átváltás EOV méterekre
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 3. Felbontás (Resolution) és BBOX számítás
        # A 156543.0339... az egyenlítői kerület / 256
        res = 156543.03392804097 / (2**z)
        size = res * 256
        
        # MEPAR BBOX: minX, minY, maxX, maxY (EOV méterben)
        # Fontos: Az EOV-ban az X a vízszintes (Kelet), Y a függőleges (Észak)
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. MEPAR WMS URL
        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0"
        }

        # 5. Letöltés
        r = requests.get(mepar_url, headers=headers, impersonate="chrome124", timeout=15)
        
        if r.status_code == 200:
            return Response(r.content, mimetype='image/png')
        return f"Hiba: {r.status_code}", 502

    except Exception as e:
        return str(e), 500

app = app
