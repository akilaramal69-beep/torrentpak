import os
import sys
import asyncio
import time
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import urllib.parse
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
    # Fix single slash typos like https:/domain.com
    JACKETT_URL = re.sub(r'^(https?):/([^/])', r'\1://\2', RAW_JACKETT_URL)

JACKETT_API_KEY = os.getenv('JACKETT_API_KEY') or os.getenv('VITE_JACKETT_API_KEY')

# HTTP Session for connection pooling (faster repeated requests)
http_session = requests.Session()
http_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/categories', methods=['GET'])
@cache.cached(timeout=3600)  # Cache for 1 hour
def get_categories():
    """Return static category list - fast and reliable"""
    return jsonify({
        'categories': [
            {'id': '2000', 'name': '🎬 Movies'},
            {'id': '2040', 'name': '🎥 Movies HD'},
            {'id': '2045', 'name': '🎥 Movies 4K'},
            {'id': '5000', 'name': '📺 TV Shows'},
            {'id': '5040', 'name': '📺 TV HD'},
            {'id': '5045', 'name': '📺 TV 4K'},
            {'id': '5070', 'name': '🎌 Anime'},
            {'id': '3000', 'name': '🎵 Music'},
            {'id': '3030', 'name': '🎧 Audiobooks'},
            {'id': '4000', 'name': '🎮 PC Games'},
            {'id': '1000', 'name': '🕹️ Console'},
            {'id': '6000', 'name': '💻 Software'},
            {'id': '7000', 'name': '📚 Books'},
            {'id': '7030', 'name': '📖 Comics'},
            {'id': '8000', 'name': '📦 Other'},
        ]
    })

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
                internal_test += " (Indexers call returned non-JSON)"
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

# Comprehensive list of stable public trackers
PUBLIC_TRACKERS = [
    'udp://tracker.opentrackr.org:1337/announce',
    'udp://open.tracker.cl:1337/announce',
    'udp://9.rarbg.com:2810/announce',
    'udp://tracker.openbittorrent.com:80/announce',
    'udp://opentracker.i2p.rocks:6969/announce',
    'udp://tracker.internetwarriors.net:1337/announce',
    'udp://tracker.leechers-paradise.org:6969/announce',
]

def enrich_results(data):
    results = data.get('Results', [])
    tracker_query = "&".join([f"tr={urllib.parse.quote(t)}" for t in PUBLIC_TRACKERS])
    
    for idx, res in enumerate(results):
        # Safety check: Ensure item is a dict
        if not isinstance(res, dict):
            continue

        # Generate an ID if missing (crucial for frontend keys/filtering)
        if 'Id' not in res:
             res['Id'] = idx + 1
             
        # Ensure Indexer exists (Jackett usually sends Tracker)
        if 'Indexer' not in res:
            res['Indexer'] = res.get('Tracker', 'Unknown')
            
        # Normalize fields
        jackett_magnet = res.get('MagnetUri')
        link = res.get('Link')
        info_hash = res.get('InfoHash')
        
        final_magnet = None
        
        # 1. Prefer original magnet if it's valid
        if jackett_magnet and str(jackett_magnet).startswith('magnet:'):
            final_magnet = jackett_magnet
        # 2. Check if Link is actually a magnet
        elif link and str(link).startswith('magnet:'):
            final_magnet = link
        # 3. Construct from InfoHash if available
        elif info_hash:
            name = urllib.parse.quote(res.get('Title', 'download'))
            final_magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
            
        if final_magnet:
            # Only add extra trackers if the magnet seems to be missing them
            if 'tr=' not in final_magnet:
                sep = '&' if '?' in final_magnet else '?'
                final_magnet = f"{final_magnet}{sep}{tracker_query}"
            res['MagnetUri'] = final_magnet
        else:
            # Clear it so the frontend knows we don't have a reliable magnet
            res['MagnetUri'] = None
            
    return data

@app.route('/api/search', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def search_torrents():
    query = request.args.get('q')
    category = request.args.get('category', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Advanced Query Normalization for better Jackett matching
    # Step 1: Normalize unicode characters (convert accented chars like é to e)
    query = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('ascii')
    
    # Step 2: Replace common filename separators with spaces
    query = re.sub(r'[._\-]+', ' ', query)
    
    # Step 3: Remove most special characters but keep alphanumeric, spaces, and colons (:)
    query = re.sub(r'[^\w\s:]', '', query)
    
    # Step 4: Collapse multiple spaces into one and strip
    query = re.sub(r'\s+', ' ', query).strip()
    
    try:
        if not JACKETT_URL or not JACKETT_API_KEY:
            print("❌ Search failed: Jackett key or URL missing", file=sys.stderr)
            return jsonify({'error': 'Jackett not configured'}), 500

        # Smart fallback: Try the configured URL first, then the internal Docker URL
        base_urls = []
        if JACKETT_URL:
            base_urls.append(JACKETT_URL.rstrip('/'))
        base_urls.append("http://jackett:9117")
        
        paths = ["/api/v2.0/indexers/all/results", "/jackett/api/v2.0/indexers/all/results"]
        
        last_error = None
        for base in base_urls:
            for path in paths:
                try:
                    url = f"{base}{path}"
                    params = {
                        'apikey': JACKETT_API_KEY,
                        'Query': query
                    }
                    
                    # Support both Category and Category[] just in case
                    if category and category != 'all' and category != 'undefined' and category != '':
                        params['Category[]'] = category
                        
                    print(f"🔍 Trying Jackett: {url} (query: {query}, cat: {category})", file=sys.stderr, flush=True)
                    # Use session for connection pooling, verify=False for self-signed certs
                    response = http_session.get(url, params=params, timeout=30, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            data = enrich_results(data)
                            results = data.get('Results', [])
                            
                            # Strict Category Filtering (Post-Fetch)
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
                                except Exception as filter_e:
                                    print(f"⚠️ Category filter error: {filter_e}", file=sys.stderr)
                                    pass

                            # Relevance Filtering (Post-Fetch)
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
                                        print(f"🎯 Relevance filter: {len(relevant_results)} results match query words", file=sys.stderr)
                                except Exception as rel_e:
                                    print(f"⚠️ Relevance filter error: {rel_e}", file=sys.stderr)
                                    pass

                            data['Results'] = results
                            print(f"✅ SUCCESS: Found {len(results)} results using {url}", file=sys.stderr, flush=True)
                            return jsonify(data)
                        except ValueError as e:
                            print(f"❌ Jackett JSON decode error: {e}", file=sys.stderr)
                            last_error = f"Invalid response from Indexer: {e}"
                            continue
                    
                    last_error = f"Jackett error {response.status_code}"
                except Exception as e:
                    print(f"⚠️ {url} failed: {str(e)}", file=sys.stderr, flush=True)
                    last_error = str(e)
        
    except Exception as global_e:
        print(f"🔥 CRITICAL SEARCH CRASH: {str(global_e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal Search Error. Please try again.'}), 502

    return jsonify({'error': last_error or "Could not reach Jackett. Check indexers and API key."}), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
