from flask import Flask, request, Response
from curl_cffi import requests
from pyproj import Transformer
import math

app = Flask(__name__)

# 1. Átváltó definiálása: Web Mercator (Locus) -> EOV (MEPAR)
# Mindig XY sorrendben (Lon, Lat / Kelet, Észak)
transformer = Transformer.from_crs("EPSG:3857", "EPSG:23700", always_xy=True)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "MEPAR EOV-WGS84 Átváltó Proxy Aktív", 200

    # Locus paraméterek (x, y, z)
    try:
        z = int(args.get('tilematrix', args.get('z', 0)))
        x = int(args.get('tilecol', args.get('x', 0)))
        y = int(args.get('tilerow', args.get('y', 0)))
    except:
        return "Hibás x,y,z paraméterek", 400

    # 2. MATEK: Mercator csempe -> EOV koordináta
    # Kiszámoljuk a csempe közepét méterben (Mercator EPSG:3857)
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    
    # Átváltás: GPS -> Mercator Méter -> EOV Méter
    # (A pyproj-nak közvetlenül is megadhatjuk a Mercatort)
    world_merc_x = (x / n * 40075016.68) - 20037508.34
    world_merc_y = 20037508.34 - (y / n * 40075016.68)
    
    eov_x, eov_y = transformer.transform(world_merc_x, world_merc_y)

    # 3. MEPAR EOV Mátrix illesztés
    # Ez a rész a legnehezebb: a Locus 'z' szintje nem ugyanaz, mint a MEPAR 'z' szintje.
    # Teszteléshez most fixen a te 5-ös szintedet használjuk a kért koordináta közelében.
    mepar_z = z 
    mepar_col = int(x) # Itt még finomítani kell a mátrixot!
    mepar_row = int(y)

    # 4. Kérés összeállítása a te korábbi jól működő fejléceiddel
    final_params = (
        f"viewparams=VONEV:null;IGDAT:null"
        f"&SRS=EPSG:23700"
        f"&layer=iier:topo10&style=raster&tilematrixset=EOV_teszt"
        f"&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/png"
        f"&TileMatrix=EOV_teszt:{mepar_z}&TileCol={mepar_col}&TileRow={mepar_row}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "Origin": "https://mepar.mvh.allamkincstar.gov.hu",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Sec-Fetch-Site": "same-origin", # Visszaállítva a te példádra
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "image"
    }

    try:
        # TLS Impersonate használata a 400-as hiba ellen
        resp = requests.get(f"{TARGET_URL}?{final_params}", headers=headers, impersonate="chrome124", timeout=15)
        return Response(resp.content, status=resp.status_code, content_type="image/png")
    except Exception as e:
        return str(e), 500
