from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse

app = Flask(__name__)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Bejövő paraméterek
    args = dict(request.args)
    
    if not args:
        return "Proxy OK, várjuk a Locus kérését!", 200

    # --- KRITIKUS MEPAR JAVÍTÁSOK ---
    
    # 1. Viewparams kényszerítése (E nélkül 400-at dob)
    args['viewparams'] = 'VONEV:null;IGDAT:null'
    
    # 2. PNG8 javítása (A MEPAR csak image/png-t fogad)
    if args.get('FORMAT') == 'image/png8' or args.get('format') == 'image/png8':
        args['FORMAT'] = 'image/png'

    # 3. Kisbetű/Nagybetű egységesítése (Néha ezen is elúszik)
    # A MEPAR a nagybetűs SERVICE, REQUEST, LAYER paramétereket szereti
    final_args = {}
    for k, v in args.items():
        final_args[k.upper()] = v

    # Új URL összeállítása
    encoded_args = urllib.parse.urlencode(final_args)
    final_url = f"{TARGET_URL}?{encoded_args}"

    try:
        # curl_cffi használata a Chrome ujjlenyomat miatt
        resp = requests.get(final_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        
        # Ha a MEPAR még mindig 400-at dob, küldjük vissza a hibaüzenetét
        if resp.status_code != 200:
            return Response(f"MEPAR hiba: {resp.text}", status=resp.status_code)

        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    
    except Exception as e:
        return f"Proxy belső hiba: {str(e)}", 500
