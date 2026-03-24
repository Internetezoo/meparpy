from flask import Flask, request, Response
import requests
import math

app = Flask(__name__)

def wgs84_to_eov(lat, lon):
    """
    Egyszerűsített WGS84 -> EOV átszámítás a MEPAR koordinátákhoz.
    """
    east = (lon - 19.04833) * 72000 + 650000
    north = (lat - 47.14444) * 111100 + 200000
    return east, north

def get_tile_bounds(z, x, y):
    """
    Kiszámolja a csempe (tile) WGS84 határait.
    """
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

@app.route('/api/tile/<int:z>/<int:x>/<int:y>.png')
def mepar_proxy(z, x, y):
    # 1. Koordináta számítás (Csempe bal felső sarka)
    lat, lon = get_tile_bounds(z, x, y)
    
    # 2. Átváltás EOV-ra (A MEPAR ezt eszi meg)
    eov_x, eov_y = wgs84_to_eov(lat, lon)
    
    # 3. MEPAR BBOX kiszámítása (kb. 500 méteres környezet a zoomtól függően)
    # Ez egy közelítés, a pontosabb képhez a z-szinttel kellene skálázni
    diff = 1000 / (2 ** (z - 10)) if z > 10 else 2000
    bbox = f"{eov_x},{eov_y-diff},{eov_x+diff},{eov_y}"

    # 4. MEPAR URL összeállítása
    mepar_url = (
        "https://mepar.mvh.allamkincstar.gov.hu/arcgis/services/mepar/mepar_f_2023/MapServer/WMSServer?"
        "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={}&"
        "CRS=EPSG:23700&WIDTH=256&HEIGHT=256&LAYERS=1,2,3&"
        "STYLES=&FORMAT=image/png&TRANSPARENT=TRUE"
    ).format(bbox)

    # 5. Lekérés a MEPAR-tól (Referer fejléccel, hogy ne dobjon ki)
    headers = {
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        print(f"Lekérés: z={z}, x={x}, y={y} -> BBOX: {bbox}")
        resp = requests.get(mepar_url, headers=headers, timeout=10)
        return Response(resp.content, mimetype='image/png')
    except Exception as e:
        print(f"Hiba: {e}")
        return "Hiba a letöltéskor", 500

# Alapértelmezett útvonal a teszteléshez
@app.route('/')
def home():
    return "MEPAR Proxy Online. Használd az /api/tile/z/x/y.png formátumot!"

if __name__ == '__main__':
    app.run(debug=True)
