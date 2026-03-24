from flask import Flask, request, Response
from curl_cffi import requests

app = Flask(__name__)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "Proxy OK - Várakozás a Locus-ra", 200

    # Adatok kinyerése
    # Locus-ból jöhet kis- és nagybetűvel is, lekezeljük:
    z = str(args.get('tilematrix', args.get('TILEMATRIX', '5'))).split(':')[-1]
    x = str(args.get('tilecol', args.get('TILECOL', '0')))
    y = str(args.get('tilerow', args.get('TILEROW', '0')))

    # PONTOSAN a te példád szerinti URL felépítése kézzel
    # Megjegyzés: a %3A a kettőspont (:), a %2F a per jel (/)
    query = (
        f"viewparams=VONEV:null;IGDAT:null"
        f"&SRS=EPSG:23700"
        f"&layer=iier%3Atopo10"
        f"&style=raster"
        f"&tilematrixset=EOV_teszt"
        f"&Service=WMTS"
        f"&Request=GetTile"
        f"&Version=1.0.0"
        f"&Format=image%2Fpng"
        f"&TileMatrix=EOV_teszt%3A{z}"
        f"&TileCol={x}"
        f"&TileRow={y}"
    )

    final_url = f"{TARGET_URL}?{query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    }

    try:
        # Az impersonate="chrome124" kulcsfontosságú a TLS ujjlenyomat miatt!
        resp = requests.get(final_url, headers=headers, impersonate="chrome124", timeout=15)
        
        if resp.status_code != 200:
            return Response(f"MEPAR hiba kód: {resp.status_code}\nURL: {final_url}\nValasz: {resp.text}", status=resp.status_code)

        return Response(resp.content, status=200, content_type="image/png")
    
    except Exception as e:
        return f"Proxy hiba: {str(e)}", 500
