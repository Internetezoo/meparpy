from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse

app = Flask(__name__)

# A példád alapú cél URL
TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Locusból jövő nyers adatok
    incoming_args = dict(request.args)
    
    if not incoming_args:
        return "Proxy fut! A Locus-ban az URL végén legyenek ott a paraméterek.", 200

    # PONTOSAN A PÉLDÁD SZERINTI SORREND ÉS TARTALOM ÖSSZEÁLLÍTÁSA
    # A sorrend a MEPAR-nál néha számít a cache miatt
    ordered_params = {
        "viewparams": "VONEV:null;IGDAT:null",
        "SRS": "EPSG:23700",
        "layer": incoming_args.get("LAYER", incoming_args.get("layer", "iier:topo10")),
        "style": "raster",
        "tilematrixset": "EOV_teszt",
        "Service": "WMTS",
        "Request": "GetTile",
        "Version": "1.0.0",
        "Format": "image/png",
        "TileMatrix": f"EOV_teszt:{incoming_args.get('TILEMATRIX', incoming_args.get('tilematrix', '5')).split(':')[-1]}",
        "TileCol": incoming_args.get("TILECOL", incoming_args.get("tilecol", "0")),
        "TileRow": incoming_args.get("TILEROW", incoming_args.get("tilerow", "0"))
    }

    # URL kódolás (az & és = jelek megtartásával)
    final_url = f"{TARGET_URL}?{urllib.parse.urlencode(ordered_params)}"

    try:
        # Chrome emuláció a curl_cffi-vel
        resp = requests.get(final_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        
        # Ha 400-as hiba van, írjuk ki a MEPAR válaszát, hogy lássuk mi a baj
        if resp.status_code != 200:
            return Response(f"MEPAR hiba: {resp.text}", status=resp.status_code, content_type="text/plain")

        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type", "image/png"))

    except Exception as e:
        return f"Proxy hiba: {str(e)}", 500
