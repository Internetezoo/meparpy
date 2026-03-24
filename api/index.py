from flask import Flask, Response
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# GPS (4326) -> EOV (23700)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

# A main.js-ben talált TopLeftCorner (EOV méterben)
ORIGIN_X = 421306.58134742436
ORIGIN_Y = 366630.91008161334

def get_tile_bounds(z, x, y):
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/')
def home():
    return "MEPAR Proxy Fut (WMTS mód)"

@app.route('/<int:z>/<int:x>/<int:y>.png')
def proxy(z, x, y):
    try:
        # 1. Átváltás GPS -> EOV
        lat, lon = get_tile_bounds(z, x, y)
        eov_x, eov_y = transformer.transform(lon, lat)

        # 2. WMTS TileMatrix kiszámítása (a JS-ben lévő adatok alapján)
        # A MEPAR-nál a zoom szintek eltolva lehetnek. 
        # Próbáljuk meg a direkt WMS-t 1.1.1-es verzióval, mert az a legbiztosabb:
        
        url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&"
            f"BBOX={eov_x-100},{eov_y-100},{eov_x+100},{eov_y+100}&" # Teszt ablak
            "SRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        )
        
        # Ha a BBOX-szal baj van, próbáljuk meg a csempe alapú lekérést:
        res = 156543.033928 / (2**z)
        size = res * 256
        bbox_real = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"
        
        final_url = url.replace(f"{eov_x-100},{eov_y-100},{eov_x+100},{eov_y+100}", bbox_real)

        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }

        r = requests.get(final_url, headers=headers, impersonate="chrome124", timeout=15)
        
        # Ha hibát kapunk, próbáljuk meg a rétegek nélkül (csak a 0-ás réteg)
        if r.status_code != 200 or len(r.content) < 1000:
            final_url = final_url.replace("LAYERS=1,2,3", "LAYERS=0")
            r = requests.get(final_url, headers=headers, impersonate="chrome124")

        return Response(r.content, mimetype='image/png')

    except Exception as e:
        return str(e), 500

app = app
