from flask import Flask, Response
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# GPS -> EOV transzformátor
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Locus csempe sarkaiból GPS koordinátát számol"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/<int:z>/<int:x>/<int:y>.png')
def proxy(z, x, y):
    try:
        # 1. GPS koordináták
        lat, lon = get_tile_bounds(z, x, y)
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 2. A JS-ből kiolvasott pontos felbontási állandó
        # Web Mercator felbontás az egyenlítőnél
        res = 156543.03392804097 / (2**z)
        size = res * 256
        
        # 3. MEPAR BBOX (minX, minY, maxX, maxY)
        # Az EOV-ban az X a Keleti, Y az Északi irány
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. A JS-ben talált réteg: iier:topo10 helyett próbáljuk a mepar_f_2023-at
        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }

        # 5. Lekérés curl_cffi-vel
        r = requests.get(mepar_url, headers=headers, impersonate="chrome124", timeout=15)
        
        # Ha hibát ad (pl. XML hibaüzenet), küldjük vissza a státuszt
        if r.status_code != 200:
            return Response(f"Hiba: {r.status_code}", status=502)

        return Response(r.content, mimetype='image/png')

    except Exception as e:
        return str(e), 500

app = app
