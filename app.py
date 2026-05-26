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
import bencode
import hashlib
from flask_caching import Cache
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'torrentwave_secret_key')
CORS(app)

# Configure Flask-Caching with Redis
cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_DEFAULT_TIMEOUT": 1800  # Cache search results for 30 minutes
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
            res['FallbackLink'] = link
            
    return data

# Bitmagnet GraphQL - Direct query for accurate seeder/leecher counts
BITMAGNET_URL = os.getenv('BITMAGNET_URL', 'http://bitmagnet:3333')

# Map Bitmagnet contentType to Jackett category IDs and display names
BITMAGNET_CATEGORY_MAP = {
    'movie': {'id': 2000, 'name': '🎬 Movies'},
    'tv_show': {'id': 5000, 'name': '📺 TV Shows'},
    'music': {'id': 3000, 'name': '🎵 Music'},
    'ebook': {'id': 7000, 'name': '📚 Books'},
    'comic': {'id': 7030, 'name': '📖 Comics'},
    'audiobook': {'id': 3030, 'name': '🎧 Audiobooks'},
    'software': {'id': 6000, 'name': '💻 Software'},
    'game': {'id': 4000, 'name': '🎮 Games'},
    'xxx': {'id': 8000, 'name': '📦 Other'},
}

# Reverse map: Jackett category IDs to Bitmagnet contentType
JACKETT_TO_BITMAGNET = {
    '2000': 'movie', '2040': 'movie', '2045': 'movie',
    '5000': 'tv_show', '5040': 'tv_show', '5045': 'tv_show', '5070': 'tv_show',
    '3000': 'music',
    '3030': 'audiobook',
    '4000': 'game', '1000': 'game',
    '6000': 'software',
    '7000': 'ebook', '7030': 'comic',
}

def search_bitmagnet(query, category=None, limit=200):
    """Query Bitmagnet GraphQL API directly for accurate seeder/leecher counts"""
    try:
        # Better query handling: append wildcard to each word for partial matching
        search_terms = query.split()
        broad_query = ' '.join([f"{word}*" for word in search_terms if len(word) >= 2])
        if not broad_query:
            broad_query = f"{query}*"
        
        # NOTE: filtering by contentType in GraphQL can be brittle if types don't match exactly.
        # We fetch broader results and filter in Python to be safe.
        
        graphql_query = {
            "query": """
                query Search($query: String!, $limit: Int) {
                    torrentContent {
                        search(input: { queryString: $query, limit: $limit }) {
                            items {
                                infoHash
                                title
                                contentType
                                seeders
                                leechers
                                publishedAt
                                torrent {
                                    name
                                    size
                                    magnetUri
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "query": broad_query,
                "limit": limit
            }
        }
        
        response = http_session.post(
            f"{BITMAGNET_URL}/graphql",
            json=graphql_query,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"⚠️ Bitmagnet returned {response.status_code}", file=sys.stderr)
            return []
            
        data = response.json()
        
        if data.get('errors'):
            print(f"⚠️ Bitmagnet GraphQL error: {data['errors']}", file=sys.stderr)
            return []
            
        items = data.get('data', {}).get('torrentContent', {}).get('search', {}).get('items', [])
        
        # Convert to Jackett-compatible format
        results = []
        tracker_query = "&".join([f"tr={urllib.parse.quote(t)}" for t in PUBLIC_TRACKERS])
        
        target_cat_id = int(category) if category and category.isdigit() else None
        
        for idx, item in enumerate(items):
            # Map contentType to category
            content_type = (item.get('contentType') or '').lower()
            cat_info = BITMAGNET_CATEGORY_MAP.get(content_type, {'id': 8000, 'name': '📦 Other'})
            
            # Python-side Category Filtering
            if target_cat_id:
                # If mapped ID doesn't match requested ID
                if cat_info['id'] != target_cat_id:
                    # Special case: requested 2040/2045 (HD/4K) should match 2000 (Movies)
                    if not (str(target_cat_id).startswith('20') and cat_info['id'] == 2000):
                        if not (str(target_cat_id).startswith('50') and cat_info['id'] == 5000):
                            continue

            torrent = item.get('torrent', {})
            magnet = torrent.get('magnetUri') or f"magnet:?xt=urn:btih:{item.get('infoHash')}&dn={urllib.parse.quote(item.get('title', ''))}"
            
            # Add trackers if missing
            if magnet and 'tr=' not in magnet:
                magnet = f"{magnet}&{tracker_query}"
            
            results.append({
                'Id': f"bm_{idx}_{item.get('infoHash', '')[:8]}",
                'Title': torrent.get('name') or item.get('title', 'Unknown'),
                'Size': torrent.get('size', 0),
                'Seeders': int(item.get('seeders') or 0),
                'Peers': int(item.get('leechers') or 0),
                'PublishDate': item.get('publishedAt', ''),
                'MagnetUri': magnet,
                'Indexer': 'bitmagnet',
                'CategoryDesc': cat_info['name'],
                'Category': [cat_info['id']],
                'Details': None,  # Explicitly None to prevent "View on Tracker"
                'InfoHash': item.get('infoHash', '')
            })
        
        print(f"🧲 Bitmagnet returned {len(results)} results (after filter)", file=sys.stderr)
        return results
        
    except Exception as e:
        print(f"⚠️ Bitmagnet query failed: {e}", file=sys.stderr)
        return []

def search_magnetz(query, timeout=15):
    """Query magnetz.eu API directly"""
    try:
        url = "https://magnetz.eu/api/magnets/search"
        params = {'query': query, 'page': 1}
        print(f"🔍 Searching Magnetz: {url}", file=sys.stderr, flush=True)
        
        response = http_session.get(url, params=params, timeout=timeout)
        if response.status_code != 200:
            print(f"⚠️ Magnetz returned {response.status_code}", file=sys.stderr)
            return []
            
        data = response.json()
        items = data.get('data', [])
        
        results = []
        tracker_query = "&".join([f"tr={urllib.parse.quote(t)}" for t in PUBLIC_TRACKERS])
        
        for item in items:
            magnet = item.get('magnet_link')
            if magnet and 'tr=' not in magnet:
                magnet = f"{magnet}&{tracker_query}"
                
            results.append({
                'Id': f"mz_{item.get('sqid', '')}",
                'Title': item.get('name', 'Unknown'),
                'Size': item.get('size', 0),
                'Seeders': int(item.get('seeders') or 0),
                'Peers': int(item.get('leechers') or 0),
                'PublishDate': item.get('created_at', ''),
                'MagnetUri': magnet,
                'Indexer': 'Magnetz',
                'CategoryDesc': 'All',
                'Category': [8000],
                'Details': item.get('web_url'),
                'InfoHash': item.get('info_hash', '')
            })
            
        print(f"🧲 Magnetz returned {len(results)} results", file=sys.stderr)
        return results
    except Exception as e:
        print(f"⚠️ Magnetz search error: {e}", file=sys.stderr)
        return []

def search_jackett(query, category=None, timeout=20):
    """Wrapper to search Jackett with strict timeout"""
    try:
        if not JACKETT_API_KEY:
            return []

        # SPEED: Try internal Docker URL first (fastest), then configured URL
        base_urls = ["http://jackett:9117"]
        if JACKETT_URL and "jackett:9117" not in JACKETT_URL:
            base_urls.append(JACKETT_URL.rstrip('/'))
        
        path = "/api/v2.0/indexers/all/results"
        
        # Try each Jackett URL until one works
        for base in base_urls:
            try:
                url = f"{base}{path}"
                params = {
                    'apikey': JACKETT_API_KEY,
                    'Query': query
                }
                
                if category and category != 'all' and category != 'undefined' and category != '':
                    params['Category[]'] = category
                    
                print(f"🔍 Searching Jackett: {url}", file=sys.stderr, flush=True)
                response = http_session.get(url, params=params, timeout=timeout, verify=False)
                
                if response.status_code == 200:
                    data = response.json()
                    data = enrich_results(data)
                    path_results = data.get('Results', [])
                    
                    # Apply Category Filtering to Jackett results immediately
                    if category and category != 'all':
                        target_cat = int(category)
                        filtered_path_results = []
                        for r in path_results:
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
                                filtered_path_results.append(r)
                        path_results = filtered_path_results

                    print(f"✅ Jackett found {len(path_results)} results", file=sys.stderr)
                    return path_results
                else:
                    print(f"⚠️ Jackett returned {response.status_code}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Jackett connection failed: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"⚠️ Jackett search error: {e}", file=sys.stderr)

    return []

@app.route('/api/resolve_magnet', methods=['GET'])
def resolve_magnet():
    url = request.args.get('url')
    title = request.args.get('title', 'download')
    info_hash_hint = request.args.get('infohash', '')  # Optional hint from frontend
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    tracker_query = "&".join([f"tr={urllib.parse.quote(t)}" for t in PUBLIC_TRACKERS])

    # Strategy 0: If we already have an InfoHash (passed as hint), build magnet immediately
    if info_hash_hint and len(info_hash_hint) in (32, 40):
        magnet = f"magnet:?xt=urn:btih:{info_hash_hint}&dn={urllib.parse.quote(title)}&{tracker_query}"
        return jsonify({'magnet': magnet})

    # Strategy 1: InfoHash embedded in the URL itself (common pattern: /torrent/HASH or ?hash=HASH)
    hash_in_url = re.search(r'(?:infohash|btih|hash)[=/:]([a-fA-F0-9]{40})', url, re.IGNORECASE)
    if hash_in_url:
        magnet = f"magnet:?xt=urn:btih:{hash_in_url.group(1)}&dn={urllib.parse.quote(title)}&{tracker_query}"
        return jsonify({'magnet': magnet})

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        resp = http_session.get(url, timeout=12, verify=False, headers=headers, allow_redirects=True)

        if resp.status_code == 200:
            content_text = resp.text
            content_decoded = urllib.parse.unquote(content_text)

            def clean_magnet(m):
                """Normalize a scraped magnet string: fix &amp; encoding, strip trailing junk."""
                m = m.replace('&amp;', '&')
                m = re.sub(r'["\'>)\s].*$', '', m, flags=re.DOTALL)
                return m

            # Strategy 2: Scan raw HTML for plain magnet links (href="magnet:..." or text)
            magnet_match = re.search(
                r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,40}(?:[^"\'<\s]|&amp;)*',
                content_text, re.IGNORECASE
            )
            if not magnet_match:
                # Strategy 3: URL-decoded content (handles magnet%3A%3F... encoding)
                magnet_match = re.search(
                    r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,40}(?:[^"\'<\s]|&amp;)*',
                    content_decoded, re.IGNORECASE
                )

            if magnet_match:
                magnet = clean_magnet(magnet_match.group(0))
                if 'tr=' not in magnet:
                    magnet = f"{magnet}&{tracker_query}"
                return jsonify({'magnet': magnet})

            # Strategy 4: Extract InfoHash from embedded .torrent file URLs (e.g. itorrents.net/torrent/HASH.torrent)
            torrent_url_hash = re.search(
                r'/torrent/([a-fA-F0-9]{40})\.torrent',
                content_text, re.IGNORECASE
            )
            if torrent_url_hash:
                magnet = f"magnet:?xt=urn:btih:{torrent_url_hash.group(1)}&dn={urllib.parse.quote(title)}&{tracker_query}"
                return jsonify({'magnet': magnet})

            # Strategy 5: Extract just the InfoHash from anywhere in the page
            hash_match = re.search(r'urn:btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})', content_text, re.IGNORECASE)
            if hash_match:
                magnet = f"magnet:?xt=urn:btih:{hash_match.group(1)}&dn={urllib.parse.quote(title)}&{tracker_query}"
                return jsonify({'magnet': magnet})

            # Strategy 6: Fall back to parsing response as .torrent file
            try:
                data = bencode.bdecode(resp.content)
                if b'info' in data:
                    info_hash = hashlib.sha1(bencode.bencode(data[b'info'])).hexdigest()
                    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(title)}&{tracker_query}"
                    return jsonify({'magnet': magnet})
            except Exception:
                pass

        return jsonify({'error': f'Could not find magnet link (HTTP {resp.status_code})'}), 400
    except Exception as e:
        print(f"⚠️ Resolve magnet error: {e}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500

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
    
    # Step 3: Replace all other non-alphanumeric characters (like : , ! ?) with spaces
    # This fixes issues where "Title:" fails to match "Title" in filenames
    query = re.sub(r'[^\w\s]', ' ', query)
    
    # Step 4: Collapse multiple spaces into one and strip
    query = re.sub(r'\s+', ' ', query).strip()
    
    jackett_results = []
    bitmagnet_results = []
    errors = []

    jackett_results = []
    bitmagnet_results = []
    magnetz_results = []
    errors = []

    # Parallel Execution: Search all sources concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_jackett = executor.submit(search_jackett, query, category, 60)
        future_bitmagnet = executor.submit(search_bitmagnet, query, category, 100)
        future_magnetz = executor.submit(search_magnetz, query, 15)
        
        import time as _time
        _deadline = _time.time() + 25  # 25s hard wall-clock limit for all sources

        # Wait for all futures simultaneously, each with a shrinking timeout
        for future, name, results_list in [
            (future_jackett, 'Jackett', 'jackett'),
            (future_bitmagnet, 'Bitmagnet', 'bitmagnet'),
            (future_magnetz, 'Magnetz', 'magnetz'),
        ]:
            remaining = max(0.5, _deadline - _time.time())
            try:
                result = future.result(timeout=remaining)
                if name == 'Jackett':
                    jackett_results = result
                elif name == 'Bitmagnet':
                    bitmagnet_results = result
                else:
                    magnetz_results = result
            except Exception as e:
                print(f"⚠️ {name} execution error: {e}", file=sys.stderr)
                errors.append(f"{name}: {e}")

    # --- 3. MERGE & DEDUPLICATE ---
    seen_hashes = set()
    final_results = []
    
    # Add Bitmagnet results first (accurate peers)
    for r in bitmagnet_results:
        h = r.get('InfoHash', '').lower()
        if h and h not in seen_hashes:
            seen_hashes.add(h)
            final_results.append(r)
            
    # Add Magnetz results
    for r in magnetz_results:
        h = (r.get('InfoHash') or '').lower()
        if not h or h not in seen_hashes:
            final_results.append(r)
            if h:
                seen_hashes.add(h)
    
    # Add Jackett results (skip duplicates)
    for r in jackett_results:
        h = (r.get('InfoHash') or '').lower()
        if not h or h not in seen_hashes:
            final_results.append(r)
            if h:
                seen_hashes.add(h)
    
    print(f"🔀 Merged: {len(bitmagnet_results)} Bitmagnet + {len(magnetz_results)} Magnetz + {len(jackett_results)} Jackett = {len(final_results)} total", file=sys.stderr)

    # --- 4. RELEVANCE FILTERING --- (Filtering applied to ALL results)
    if query and final_results:
        try:
            # Keep Unicode letters, lowercase
            query_words = [w.lower() for w in query.split() if len(w) >= 2]
            
            if query_words:
                relevant_results = []
                for r in final_results:
                    title = (r.get('Title', '') or '').lower()
                    # Preserve Unicode letters, normalize separators
                    title_normalized = re.sub(r'[._\-\[\]\(\)]+', ' ', title)
                    
                    matches = sum(1 for word in query_words if word in title_normalized)
                    
                    # STRICT EXACT MATCH enforce by User Request
                    # ALL words must be present in the title.
                    if matches >= len(query_words):
                        relevant_results.append(r)
                
                print(f"🎯 Relevance Filter: {len(final_results)} -> {len(relevant_results)} (Removed {len(final_results) - len(relevant_results)})", file=sys.stderr)
                final_results = relevant_results
        except Exception as rel_e:
            print(f"⚠️ Relevance filter error: {rel_e}", file=sys.stderr)

    return jsonify({'Results': final_results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
