from flask import Flask, request, Response
from curl_cffi import requests
from pyproj import Transformer
import math

app = Flask(__name__)

# WGS84 Mercator (Locus: EPSG:3857) -> EOV (MEPAR: EPSG:23700)
# A 'always_xy=True' biztosítja, hogy Keleti, Északi (X, Y) sorrendet kapjunk
transformer = Transformer.from_crs("EPSG:3857", "EPSG:23700", always_xy=True)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "MEPAR Proxy OK - Matek mód aktív", 200

    # 1. Locus Mercator adatainak fogadása
    try:
        z = int(args.get('z', args.get('tilematrix', 5)))
        x = int(args.get('x', args.get('tilecol', 0)))
        y = int(args.get('y', args.get('tilerow', 0)))
    except:
        return "Hibás paraméterek", 400

    # 2. MATEK: Mercator csempe -> EOV koordináta
    # Kiszámoljuk a csempe közepét méterben (Web Mercator)
    n = 2.0 ** z
    merc_x = (x + 0.5) / n * 40075016.68557849 - 20037508.342789244
    merc_y = 20037508.342789244 - (y + 0.5) / n * 40075016.68557849

    # Átváltás EOV-ba
    eov_x, eov_y = transformer.transform(merc_x, merc_y)

    # 3. EOV koordináta -> MEPAR TileCol/TileRow számítása
    # A MEPAR fix felbontásai (Resolution) EOV egységben (m/pixel)
    # Ezek a WMTS GetCapabilities-ből jönnek
    resolutions = [
        1568.0, 784.0, 392.0, 196.0, 98.0, 49.0, 24.5, 12.25, 
        6.125, 3.0625, 1.53125, 0.765625, 0.3828125, 0.19140625, 0.095703125
    ]
    
    # MEPAR kezdőpont (bal felső sarok) EOV-ban
    origin_x = 422114.56
    origin_y = 362483.52
    
    # Megkeressük a megfelelő felbontást a zoom szinthez (Locus Z -> MEPAR Z eltolás lehetséges)
    # Általában Z_mepar = Z_locus - 2 vagy hasonló az EOV miatt
    mepar_z = z 
    res = resolutions[mepar_z] if mepar_z < len(resolutions) else resolutions[-1]

    # Kiszámoljuk, melyik MEPAR csempe esik ide
    m_col = int((eov_x - origin_x) / (res * 256))
    m_row = int((origin_y - eov_y) / (res * 256))

    # 4. Kérés összeállítása a MEPAR-nak (A te jól működő fejléceiddel)
    query = (
        f"viewparams=VONEV:null;IGDAT:null&SRS=EPSG:23700"
        f"&layer=iier%3Atopo10&style=raster&tilematrixset=EOV_teszt"
        f"&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng"
        f"&TileMatrix=EOV_teszt%3A{mepar_z}&TileCol={m_col}&TileRow={m_row}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "Sec-Fetch-Site": "same-origin"
    }

    try:
        resp = requests.get(f"{TARGET_URL}?{query}", headers=headers, impersonate="chrome124", timeout=15)
        return Response(resp.content, status=resp.status_code, content_type="image/png")
    except Exception as e:
        return f"Hiba: {str(e)}", 500
