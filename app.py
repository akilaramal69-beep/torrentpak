import os
import sys
import re
import urllib.parse
import unicodedata
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask_caching import Cache

load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'torrentwave_secret_key')
CORS(app)

# Aggressive caching - 30 min for same searches
cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_DEFAULT_TIMEOUT": 1800  # 30 minutes cache
}
cache = Cache(app, config=cache_config)

# Jackett Configuration
JACKETT_URL = os.getenv('JACKETT_URL', 'http://jackett:9117')
JACKETT_API_KEY = os.getenv('JACKETT_API_KEY') or os.getenv('VITE_JACKETT_API_KEY')

# SPEED: Optimized HTTP session with connection pooling and keep-alive
http_session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=0)  # No retries - fail fast
)
http_session.mount('http://', adapter)
http_session.mount('https://', adapter)
http_session.headers.update({
    'User-Agent': 'TorrentWave/1.0',
    'Connection': 'keep-alive',
    'Accept': 'application/json',
})

# Minimal trackers for speed
TRACKERS = 'udp://tracker.opentrackr.org:1337&tr=udp://open.tracker.cl:1337&tr=udp://tracker.openbittorrent.com:80'

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/search', methods=['GET'])
@cache.cached(timeout=1800, query_string=True)  # 30 min cache
def search():
    q = request.args.get('q', '').strip()
    cat = request.args.get('category', '')
    
    if not q:
        return jsonify({'error': 'No query'}), 400
    
    if not JACKETT_API_KEY:
        return jsonify({'error': 'Jackett not configured'}), 500
    
    # Quick normalize
    q = unicodedata.normalize('NFKD', q).encode('ascii', 'ignore').decode('ascii')
    q = re.sub(r'[._\-]+', ' ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    
    try:
        params = {'apikey': JACKETT_API_KEY, 'Query': q}
        if cat and cat not in ('all', 'undefined', ''):
            params['Category[]'] = cat
        
        # SPEED: 5 second timeout, direct internal URL
        url = "http://jackett:9117/api/v2.0/indexers/all/results"
        print(f"🔍 {q}", file=sys.stderr, flush=True)
        
        resp = http_session.get(url, params=params, timeout=5, verify=False)
        
        if resp.status_code != 200:
            return jsonify({'error': f'Jackett error {resp.status_code}'}), 502
        
        data = resp.json()
        results = data.get('Results', [])
        
        # SPEED: Simple in-place processing
        query_words = set(w.lower() for w in q.split() if len(w) >= 2)
        filtered = []
        
        for i, r in enumerate(results):
            if not isinstance(r, dict):
                continue
            
            # Basic enrichment
            r['Id'] = r.get('Id', i + 1)
            r['Indexer'] = r.get('Indexer') or r.get('Tracker', 'Unknown')
            
            # Magnet fix
            magnet = r.get('MagnetUri') or r.get('Link', '')
            if not str(magnet).startswith('magnet:'):
                h = r.get('InfoHash')
                if h:
                    magnet = f"magnet:?xt=urn:btih:{h}&dn={urllib.parse.quote(r.get('Title', 'file'))}&tr={TRACKERS}"
                else:
                    magnet = None
            r['MagnetUri'] = magnet
            
            # Relevance check (fast)
            if query_words:
                title = (r.get('Title') or '').lower()
                matches = sum(1 for w in query_words if w in title)
                if matches < max(1, len(query_words) // 2):
                    continue
            
            # Category check (fast)
            if cat and cat not in ('all', ''):
                try:
                    target = int(cat)
                    prefix = str(target)[:2]
                    cats = r.get('Category', [])
                    if isinstance(cats, (int, str)):
                        cats = [int(cats)]
                    elif isinstance(cats, list):
                        cats = [int(c) for c in cats if str(c).isdigit()]
                    
                    found = any(c == target or (str(target).endswith('00') and str(c).startswith(prefix)) for c in cats)
                    if not found:
                        continue
                except:
                    pass
            
            filtered.append(r)
        
        data['Results'] = filtered
        print(f"✅ {len(filtered)} results", file=sys.stderr, flush=True)
        return jsonify(data)
        
    except requests.Timeout:
        print("⏱️ Timeout", file=sys.stderr)
        return jsonify({'error': 'Search timeout - try fewer indexers'}), 504
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug', methods=['GET'])
def debug():
    try:
        resp = requests.get(f"http://jackett:9117/api/v2.0/indexers?apikey={JACKETT_API_KEY}", timeout=3, verify=False)
        indexers = [i.get('name') for i in resp.json() if i.get('configured')] if resp.ok else []
    except:
        indexers = []
    
    return jsonify({
        'jackett_configured': bool(JACKETT_API_KEY),
        'indexers': indexers,
        'indexer_count': len(indexers)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
