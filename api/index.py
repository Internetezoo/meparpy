import sys
from flask import Flask, request, Response, render_template_string
from curl_cffi import requests
import urllib.parse
from datetime import datetime

app = Flask(__name__)

# Memóriában tárolt log lista
recent_logs = []

# HTML Sablon a főoldalhoz
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MEPAR Proxy Log</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: monospace; background: #121212; color: #00ff00; padding: 20px; }
        .log-entry { border-bottom: 1px solid #333; padding: 5px 0; font-size: 12px; }
        .time { color: #888; }
        .url { color: #ffff00; word-break: break-all; }
        h1 { color: #fff; border-bottom: 2px solid #00ff00; }
    </style>
</head>
<body>
    <h1>Locus Map Proxy Log (Utolsó 10 kérés)</h1>
    {% for log in logs %}
    <div class="log-entry">
        <span class="time">[{{ log.time }}]</span> 
        <span class="url">{{ log.url }}</span>
    </div>
    {% else %}
    <p>Még nem érkezett kérés a Locustól...</p>
    {% endfor %}
    <p><a href="/" style="color: #007bff;">Frissítés</a></p>
</body>
</html>
"""

TARGET_URL = "https://mepar.mvh.allamkincstar.gov.hu/api/proxy/iier-gs/gwc/service/wmts"

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    args = dict(request.args)
    
    # 1. Ha nincs paraméter, megmutatjuk a logokat
    if not args:
        return render_template_string(HTML_TEMPLATE, logs=recent_logs)

    # 2. Log mentése a listába
    now = datetime.now().strftime("%H:%M:%S")
    log_msg = {"time": now, "url": request.full_path}
    recent_logs.insert(0, log_msg)
    if len(recent_logs) > 10: recent_logs.pop()

    # 3. Proxy folyamat (MEPAR javítások)
    if 'viewparams' not in args and 'VIEWPARAMS' not in args:
        args['viewparams'] = 'VONEV:null;IGDAT:null'
    
    final_url = f"{TARGET_URL}?{urllib.parse.urlencode(args)}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://mepar.mvh.allamkincstar.gov.hu/"}

    try:
        resp = requests.get(final_url, headers=headers, impersonate="chrome124", timeout=15)
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    except Exception as e:
        return f"Hiba: {str(e)}", 500
