from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse

app = Flask(__name__)

# Fix URL és fix fejlécek
TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Bejövő adatok
    args = dict(request.args)
    
    # Ha üres, ne is menjünk tovább
    if not args:
        return "Proxy OK, de kellenek paraméterek!", 200

    # KÉNYSZERÍTETT MEPAR PARAMÉTEREK (A 400-as hiba ellen)
    args['viewparams'] = 'VONEV:null;IGDAT:null'
    if args.get('FORMAT') == 'image/png8':
        args['FORMAT'] = 'image/png'

    # Új URL összerakása
    final_url = f"{TARGET_URL}?{urllib.parse.urlencode(args)}"

    try:
        # Lekérés Chrome emulációval
        resp = requests.get(final_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        
        # Válasz visszaküldése (kép vagy XML)
        return Response(
            resp.content, 
            status=resp.status_code, 
            content_type=resp.headers.get("Content-Type", "image/png")
        )
    except Exception as e:
        return f"Hiba: {str(e)}", 500
