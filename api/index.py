from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse
import re

app = Flask(__name__)

# A MEPAR valódi WMTS végpontja
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
    # 1. Lekérjük a beérkező paramétereket
    args = dict(request.args)
    
    # 2. MEPAR specifikus javítások (ha hiányoznak a Locus-ból)
    if 'viewparams' not in args and 'VIEWPARAMS' not in args:
        args['viewparams'] = 'VONEV:null;IGDAT:null'
    
    # PNG8 javítása sima PNG-re
    for k in list(args.keys()):
        if k.upper() == 'FORMAT' and 'png8' in args[k]:
            args[k] = 'image/png'

    # 3. Új URL összeállítása a MEPAR felé
    encoded_args = urllib.parse.urlencode(args)
    final_url = f"{TARGET_URL}?{encoded_args}"

    try:
        # 4. Kérés küldése a MEPAR-nak (Chrome ujjlenyomattal)
        resp = requests.get(final_url, headers=HEADERS, impersonate="chrome124", timeout=20)
        
        content = resp.content
        content_type = resp.headers.get("Content-Type", "image/png")

        # 5. HA GetCapabilities XML-t kérnek, átírjuk a linkeket a saját Vercel címünkre
        # Így a Locus/QGIS a következő kéréseket is a Proxynak küldi, nem közvetlen a MEPAR-nak
        request_type = args.get('request', args.get('REQUEST', ''))
        
        if "GetCapabilities" in request_type or "xml" in content_type:
            # Megállapítjuk a saját aktuális URL-ünket (pl. https://meparpyproxy.vercel.app)
            my_url = request.host_url.rstrip('/')
            
            # Kicseréljük a távoli címeket a sajátunkra az XML-ben
            content = content.replace(b"https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts", my_url.encode())
            content = content.replace(b"127.0.0.1/geoserver", my_url.encode())
            content = content.replace(b"127.0.0.1:8080/geoserver", my_url.encode())
            
            content_type = "text/xml; charset=UTF-8"

        # 6. Válasz visszaküldése a kliensnek
        return Response(content, status=resp.status_code, content_type=content_type)

    except Exception as e:
        return Response(f"Proxy Error: {str(e)}", status=500)

# Vercel-nek nem kell az app.run()
