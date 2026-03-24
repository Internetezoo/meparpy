from flask import Flask, Response
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# GPS (WGS84) -> EOV (EPSG:23700) átalakító
# Mindig XY sorrendben (lon, lat)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Kiszámolja a csempe bal felső sarkának GPS koordinátáit"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/<int:z>/<int:x>/<int:y>.png')
def proxy(z, x, y):
    try:
        # 1. Kiszámoljuk a Locus által kért csempe GPS sarkát
        lat, lon = get_tile_bounds(z, x, y)
        
        # 2. Átváltjuk EOV-ra
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 3. Kiszámoljuk az adott zoomhoz tartozó terület méretét (BBOX)
        # Ez a bűvös szám biztosítja, hogy a 256x256-os kocka pontos legyen
        res = 156543.03392804097 / (2**z)
        size = res * 256
        
        # MEPAR BBOX formátum: minX, minY, maxX, maxY (EOV méterben)
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. A MEPAR WMS (nem WMTS!) URL-je, ami bármilyen BBOX-ot le tud gyártani
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

        # Lekérés
        r = requests.get(mepar_url, headers=headers, impersonate="chrome124", timeout=15)
        return Response(r.content, mimetype='image/png')

    except Exception as e:
        return str(e), 500

app = app
