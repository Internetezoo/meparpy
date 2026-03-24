from flask import Flask, request, Response
from curl_cffi import requests

app = Flask(__name__)

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    if not args:
        return "Proxy OK - Várjuk a Locus kérését", 200

    # Locus paraméterek tisztítása
    z = str(args.get('tilematrix', args.get('TILEMATRIX', '5'))).split(':')[-1]
    x = str(args.get('tilecol', args.get('TILECOL', '0')))
    y = str(args.get('tilerow', args.get('TILEROW', '0')))

    # A te példád alapján összeállított query string (karakterhelyesen!)
    # A viewparams-ban a kettőspontot NEM kódoljuk, a többit igen, ahol kell
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

    # Frissített, biztonságosabb fejlécek
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9",
        "Referer": "https://mepar.mvh.allamkincstar.gov.hu/",
        "Origin": "https://mepar.mvh.allamkincstar.gov.hu",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"  # Módosítva 'same-origin'-ről, mert külső szerver vagyunk
    }

    try:
        # Az impersonate="chrome124" elengedhetetlen a TLS miatt!
        resp = requests.get(
            final_url, 
            headers=headers, 
            impersonate="chrome124", 
            timeout=15,
            verify=True # SSL ellenőrzés bekapcsolva
        )
        
        if resp.status_code != 200:
            return Response(
                f"MEPAR hiba kód: {resp.status_code}\nURL: {final_url}\nHeader: {headers.get('Sec-Fetch-Site')}\nValasz: {resp.text}", 
                status=resp.status_code
            )

        return Response(resp.content, status=200, content_type="image/png")
    
    except Exception as e:
        return f"Proxy hiba: {str(e)}", 500
