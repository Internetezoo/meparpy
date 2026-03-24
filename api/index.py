from flask import Flask, Response, request
from curl_cffi import requests
import math
from pyproj import Transformer

app = Flask(__name__)

# WGS84 (GPS) -> EOV (Magyar Egységes Országos Vetület) konverter
# Az 'always_xy=True' biztosítja, hogy a sorrend (lon, lat) -> (East, North) legyen
transformer = Transformer.from_crs("EPSG:4326", "EPSG:23700", always_xy=True)

def get_tile_bounds(z, x, y):
    """Kiszámolja a csempe bal felső sarkának WGS84 (GPS) koordinátáit"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/api/tile/<int:z>/<int:x>/<int:y>.png')
def mepar_proxy(z, x, y):
    try:
        # 1. Csempe koordináta kiszámítása (GPS)
        lat, lon = get_tile_bounds(z, x, y)
        
        # 2. Átváltás EOV-ra (Magyar vetület)
        eov_x, eov_y = transformer.transform(lon, lat)
        
        # 3. Felbontás alapú BBOX számítás (Web Mercator -> EOV közelítés)
        # 156543.03 a föld kerülete / 256 pixel a 0. zoomon
        res = 156543.03 / (2**z) 
        size = res * 256 # Egy csempe mérete méterben az adott zoomon
        
        # A MEPAR WMS bal-alsó és jobb-felső sarkot vár (minX, minY, maxX, maxY)
        bbox = f"{eov_x},{eov_y-size},{eov_x+size},{eov_y}"

        # 4. MEPAR WMS URL összeállítása (2023-as rétegek)
        mepar_url = (
            "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
            "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
            "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
        ).format(bbox)

        # 5. Fejlécek beállítása (Böngészőnek álcázzuk magunkat)
        headers = {
            "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Lekérés curl_cffi-vel (impersonate="chrome110" segít a TLS ujjlenyomatnál)
        r = requests.get(mepar_url, headers=headers, impersonate="chrome110", timeout=15)
        
        # Ha a MEPAR hibaüzenetet küld (pl. XML-t kép helyett)
        if r.status_code != 200:
             return f"MEPAR hiba: {r.status_code}", 502

        return Response(r.content, mimetype='image/png')

    except Exception as e:
        # Ez megjelenik a Vercel logban, ha hiba van
        print(f"HIBA: {str(e)}")
        return f"Szerver hiba: {str(e)}", 500

@app.route('/')
def home():
    return "MEPAR Proxy aktív. Használd a Locus-ban a megadott URL mintát!"

if __name__ == '__main__':
    app.run(debug=True)
