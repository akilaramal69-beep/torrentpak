import os
import sys
import re
import urllib.parse
import unicodedata
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from flask_caching import Cache

load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'torrentwave_secret_key')
CORS(app)

# Configure Flask-Caching with Redis
cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_DEFAULT_TIMEOUT": 600  # Cache search results for 10 minutes
}
cache = Cache(app, config=cache_config)

# Jackett Configuration
RAW_JACKETT_URL = os.getenv('JACKETT_URL') or os.getenv('VITE_JACKETT_URL')
JACKETT_URL = RAW_JACKETT_URL
if RAW_JACKETT_URL:
    JACKETT_URL = re.sub(r'^(https?):/([^/])', r'\1://\2', RAW_JACKETT_URL)

JACKETT_API_KEY = os.getenv('JACKETT_API_KEY') or os.getenv('VITE_JACKETT_API_KEY')

# HTTP Session for connection pooling - ORIGINAL WORKING CONFIG
http_session = requests.Session()
http_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# Public trackers
PUBLIC_TRACKERS = [
    'udp://tracker.opentrackr.org:1337/announce',
    'udp://open.tracker.cl:1337/announce',
    'udp://9.rarbg.com:2810/announce',
    'udp://tracker.openbittorrent.com:80/announce',
    'udp://opentracker.i2p.rocks:6969/announce',
]

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/debug', methods=['GET'])
def debug_config():
    internal_test = "Not tested"
    indexers_found = []
    
    try:
        resp = requests.get(
            f"http://jackett:9117/api/v2.0/indexers/all/results?apikey={JACKETT_API_KEY or ''}&Query=test", 
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=5, verify=False
        )
        internal_test = f"Connected (Status: {resp.status_code})"
        
        idx_resp = requests.get(
            f"http://jackett:9117/api/v2.0/indexers?apikey={JACKETT_API_KEY or ''}",
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=5, verify=False
        )
        if idx_resp.status_code == 200:
            try:
                indexers = idx_resp.json()
                indexers_found = [i.get('name') for i in indexers if i.get('configured')]
            except:
                pass
    except Exception as e:
        internal_test = f"Failed: {str(e)}"

    return jsonify({
        'jackett_url_env': JACKETT_URL,
        'jackett_key_set': bool(JACKETT_API_KEY),
        'internal_test': internal_test,
        'configured_indexers': indexers_found,
        'indexers_count': len(indexers_found),
        'server_time': datetime.now().isoformat()
    })

def enrich_results(data):
    results = data.get('Results', [])
    tracker_query = "&".join([f"tr={urllib.parse.quote(t)}" for t in PUBLIC_TRACKERS])
    
    for idx, res in enumerate(results):
        if not isinstance(res, dict):
            continue

        if 'Id' not in res:
             res['Id'] = idx + 1
             
        if 'Indexer' not in res:
            res['Indexer'] = res.get('Tracker', 'Unknown')
            
        jackett_magnet = res.get('MagnetUri')
        link = res.get('Link')
        info_hash = res.get('InfoHash')
        
        final_magnet = None
        
        if jackett_magnet and str(jackett_magnet).startswith('magnet:'):
            final_magnet = jackett_magnet
        elif link and str(link).startswith('magnet:'):
            final_magnet = link
        elif info_hash:
            name = urllib.parse.quote(res.get('Title', 'download'))
            final_magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
            
        if final_magnet:
            if 'tr=' not in final_magnet:
                sep = '&' if '?' in final_magnet else '?'
                final_magnet = f"{final_magnet}{sep}{tracker_query}"
            res['MagnetUri'] = final_magnet
        else:
            res['MagnetUri'] = None
            
    return data

@app.route('/api/search', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def search_torrents():
    query = request.args.get('q')
    category = request.args.get('category', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Query Normalization
    query = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('ascii')
    query = re.sub(r'[._\-]+', ' ', query)
    query = re.sub(r'[^\w\s:]', '', query)
    query = re.sub(r'\s+', ' ', query).strip()
    
    try:
        if not JACKETT_API_KEY:
            print("❌ Search failed: Jackett API key missing", file=sys.stderr)
            return jsonify({'error': 'Jackett not configured'}), 500

        # Direct internal URL - proven to work
        url = "http://jackett:9117/api/v2.0/indexers/all/results"
        params = {
            'apikey': JACKETT_API_KEY,
            'Query': query
        }
        
        if category and category != 'all' and category != 'undefined' and category != '':
            params['Category[]'] = category
            
        print(f"🔍 Searching: {query}", file=sys.stderr, flush=True)
        
        # 30 second timeout
        response = http_session.get(url, params=params, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            data = enrich_results(data)
            results = data.get('Results', [])
            
            # Category Filtering
            if category and category != 'all':
                try:
                    target_cat = int(category)
                    filtered_results = []
                    for r in results:
                        cat = r.get('Category', [])
                        if isinstance(cat, (int, str)):
                            cat_list = [int(cat)]
                        elif isinstance(cat, list):
                            cat_list = [int(c) for c in cat if str(c).isdigit()]
                        else:
                            continue

                        target_prefix = str(target_cat)[0:2]
                        match = False
                        for c in cat_list:
                            if c == target_cat:
                                match = True
                                break
                            if str(target_cat).endswith('00') and str(c).startswith(target_prefix):
                                match = True
                                break
                        
                        if match:
                            filtered_results.append(r)
                            
                    results = filtered_results
                except:
                    pass

            # Relevance Filtering
            if query:
                try:
                    query_words = [w.lower() for w in query.split() if len(w) >= 2]
                    
                    if query_words:
                        relevant_results = []
                        for r in results:
                            title = (r.get('Title', '') or '').lower()
                            title_normalized = re.sub(r'[._\-]+', ' ', title)
                            title_normalized = re.sub(r'[^\w\s]', '', title_normalized)
                            
                            matches = sum(1 for word in query_words if word in title_normalized)
                            required_matches = max(1, len(query_words) // 2)
                            
                            if matches >= required_matches:
                                relevant_results.append(r)
                        
                        results = relevant_results
                except:
                    pass

            data['Results'] = results
            print(f"✅ Found {len(results)} results", file=sys.stderr, flush=True)
            return jsonify(data)
        
        return jsonify({'error': f'Jackett error {response.status_code}'}), 502
        
    except requests.exceptions.Timeout:
        print("⏱️ Timeout", file=sys.stderr)
        return jsonify({'error': 'Search timeout'}), 504
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
