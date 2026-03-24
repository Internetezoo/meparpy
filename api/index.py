from flask import Flask, request, Response
from curl_cffi import requests
from pyproj import Transformer
import math

app = Flask(__name__)

# WGS84 (Locus/GPS) -> EOV (MEPAR) átváltó
to_eov = Transformer.from_crs("EPSG:3857", "EPSG:23700", always_xy=True)

# MEPAR EOV Mátrix alapadatai (EOV kezdőpont és felbontások)
# Ezek nélkülözhetetlenek a pontos átszámításhoz
ORIGIN_X = 422114.56   # EOV Nyugati szél
ORIGIN_Y = 362483.52   # EOV Északi szél
TILE_SIZE = 256        # Pixel méret

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args: return "Proxy aktív, matek üzemmód bekapcsolva.", 200

    # 1. Locus Mercator adatainak fogadása
    try:
        z = int(args.get('z', 5))
        x = int(args.get('x', 0))
        y = int(args.get('y', 0))
    except: return "Hibás paraméterek", 400

    # 2. MATEK: Mercator X,Y -> EOV X,Y konverzió (leegyszerűsítve)
    # A Locus csempe közepének kiszámítása
    world_size = 20037508.34 * 2
    res = world_size / (2**z * TILE_SIZE)
    merc_x = (x * TILE_SIZE * res) - 20037508.34
    merc_y = 20037508.34 - (y * TILE_SIZE * res)

    # Átváltás EOV-ba
    eov_x, eov_y = to_eov.transform(merc_x, merc_y)

    # 3. MATEK: EOV koordináta -> MEPAR TileCol/TileRow
    # Itt a MEPAR konkrét TileMatrixSet felbontásait kell használni (EOV_teszt)
    # Ez a rész kritikus, mert a zoom szintek nem egyeznek pontosan!
    mepar_z = z # Ez csak közelítés, a valóságban eltolás kellhet
    
    # MEPAR URL összeállítása
    target_url = f"https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"
    params = (
        f"viewparams=VONEV:null;IGDAT:null"
        f"&Service=WMTS&Request=GetTile&Version=1.0.0"
        f"&Layer=iier:topo10&Style=raster&Format=image/png"
        f"&TileMatrixSet=EOV_teszt&TileMatrix=EOV_teszt:{mepar_z}"
        f"&TileCol={int(eov_x/1000)}&TileRow={int(eov_y/1000)}" # Csak példa számítás!
    )

    # 4. Lekérés a MEPAR-tól
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://mepar.mvh.allamkincstar.gov.hu/"}
    resp = requests.get(f"{target_url}?{params}", headers=headers, impersonate="chrome124")

    return Response(resp.content, content_type="image/png")
