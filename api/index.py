from flask import Flask, request, Response
from curl_cffi import requests
import urllib.parse

app = Flask(__name__)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "Proxy OK - Várakozás paraméterekre", 200

    # Kinyerjük a számot a tilematrixból (Locusnál ez csak egy szám, pl '5')
    raw_z = str(args.get('tilematrix', args.get('TILEMATRIX', '5')))
    z_num = raw_z.split(':')[-1] # Ha 'EOV_teszt:5', akkor '5' lesz

    # PONTOSAN a te példád szerinti paraméterek és sorrend
    params = [
        ('viewparams', 'VONEV:null;IGDAT:null'),
        ('SRS', 'EPSG:23700'),
        ('layer', 'iier:topo10'),
        ('style', 'raster'),
        ('tilematrixset', 'EOV_teszt'),
        ('Service', 'WMTS'),
        ('Request', 'GetTile'),
        ('Version', '1.0.0'),
        ('Format', 'image/png'),
        ('TileMatrix', f'EOV_teszt:{z_num}'),
        ('TileCol', args.get('tilecol', args.get('TILECOL', '0'))),
        ('TileRow', args.get('tilerow', args.get('TILEROW', '0')))
    ]

    # Kézzel rakjuk össze az URL-t, hogy a sorrend FIX legyen
    query_string = "&".join([f"{k}={v}" for k, v in params])
    final_url = f"{TARGET_URL}?{query_string}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
    }

    try:
        # Chrome emuláció kötelező!
        resp = requests.get(final_url, headers=headers, impersonate="chrome124", timeout=15)
        
        # Ha nem 200 OK, akkor baj van
        if resp.status_code != 200:
            return Response(f"MEPAR hiba kód: {resp.status_code}\nVálasz: {resp.text}", status=resp.status_code)

        return Response(resp.content, status=200, content_type="image/png")
    
    except Exception as e:
        return f"Proxy hiba: {str(e)}", 500
