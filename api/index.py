from flask import Flask, request, Response
from curl_cffi import requests
from pyproj import Transformer
import math

app = Flask(__name__)

# WGS84 Mercator (Locus: EPSG:3857) -> EOV (MEPAR: EPSG:23700)
# Fontos: always_xy=True, hogy Lon, Lat (X, Y) sorrendben maradjon
transformer = Transformer.from_crs("EPSG:3857", "EPSG:23700", always_xy=True)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "MEPAR-Locus Bridge Aktív", 200

    # 1. Locus Mercator koordináták (Z, X, Y)
    try:
        z = int(args.get('z', args.get('tilematrix', 5)))
        x = int(args.get('x', args.get('tilecol', 0)))
        y = int(args.get('y', args.get('tilerow', 0)))
    except:
        return "Hibás paraméterek", 400

    # 2. MATEK: Mercator X,Y -> EOV X,Y
    # Kiszámoljuk a csempe közepének Mercator koordinátáit (méterben)
    n = 2.0 ** z
    merc_x = (x + 0.5) / n * 40075016.68557849 - 20037508.342789244
    merc_y = 20037508.342789244 - (y + 0.5) / n * 40075016.68557849

    # Átváltás EOV-ba (X=Keleti, Y=Északi)
    eov_x, eov_y = transformer.transform(merc_x, merc_y)

    # 3. EOV koordináta -> MEPAR TileCol/TileRow
    # A logod alapján 11-es zoomnál: Col=1374, Row=934
    # EOV_teszt felbontása (z=11 esetén kb. 0.896 m/pixel)
    # Ezek az állandók a MEPAR WMTS mátrixából jönnek:
    resolution = [3584, 1792, 896, 448, 224, 112, 56, 28, 14, 7, 3.5, 1.75, 0.875, 0.4375, 0.21875, 0.109375]
    res = resolution[z] if z < len(resolution) else resolution[-1]
    
    # MEPAR Origin (bal felső sarok EOV-ban)
    origin_x = 422114.56
    origin_y = 362483.52
    
    mepar_col = int((eov_x - origin_x) / (res * 256))
    mepar_row = int((origin_y - eov_y) / (res * 256))

    # 4. Lekérés a MEPAR-tól (A már bevált fejlécekkel)
    query = (
        f"viewparams=VONEV:null;IGDAT:null"
        f"&SRS=EPSG:23700&layer=iier:topo10&style=raster&tilematrixset=EOV_teszt"
        f"&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/png"
        f"&TileMatrix=EOV_teszt:{z}&TileCol={mepar_col}&TileRow={mepar_row}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "Sec-Fetch-Site": "same-origin"
    }

    try:
        resp = requests.get(f"{TARGET_URL}?{query}", headers=headers, impersonate="chrome124", timeout=15)
        return Response(resp.content, status=resp.status_code, content_type="image/png")
    except Exception as e:
        return str(e), 500
