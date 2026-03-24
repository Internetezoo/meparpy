from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse

app = Flask(__name__)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"
HEADERS = {
    "Host": "mepar.mvh.allamkincstar.gov.hu",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    # Eredeti paraméterek átvétele
    query_params = dict(request.args)
    
    # MEPAR kényszerítések (viewparams és format fix)
    if 'viewparams' not in query_params:
        query_params['viewparams'] = 'VONEV:null;IGDAT:null'
    
    # Locus néha png8-at küld, a MEPAR-nak sima png kell
    if query_params.get('format') == 'image/png8':
        query_params['format'] = 'image/png'

    final_url = f"{TARGET_URL}?{urllib.parse.urlencode(query_params)}"

    try:
        # A curl_cffi KELL a Vercelen is a TLS ujjlenyomat miatt
        resp = requests.get(final_url, headers=HEADERS, impersonate="chrome124", timeout=15)
        
        content = resp.content
        # XML címek átírása a Vercel saját URL-jére (hogy a Locus megtalálja a csempéket)
        if "GetCapabilities" in query_params.get('request', '') or "xml" in resp.headers.get("Content-Type", ""):
            my_url = request.host_url.rstrip('/')
            # Minden belső linket a saját Vercel címünkre irányítunk
            content = content.replace(b"mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts", my_url.encode())
            content = content.replace(b"127.0.0.1/geoserver", my_url.encode())

        return Response(content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    
    except Exception as e:
        return Response(str(e), status=500)

# Vercelnek kell
app.debug = False