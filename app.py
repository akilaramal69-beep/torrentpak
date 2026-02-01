import os
import sys
import asyncio
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from pikpakapi import PikPakApi
from dotenv import load_dotenv
import requests
import urllib.parse
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
from flask_caching import Cache
import redis

load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'magnet_cloud_secret_shared_key')
CORS(app)

# Configure Flask-Caching with Redis
cache_config = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": "redis",
    "CACHE_REDIS_PORT": 6379,
    "CACHE_DEFAULT_TIMEOUT": 300  # Cache search results for 5 minutes
}
cache = Cache(app, config=cache_config)

# PikPak Configuration
PIKPAK_EMAIL = os.getenv('PIKPAK_EMAIL')
PIKPAK_PASSWORD = os.getenv('PIKPAK_PASSWORD')

# Global PikPak Client
pikpak_client = None

# Jackett Configuration
RAW_JACKETT_URL = os.getenv('JACKETT_URL') or os.getenv('VITE_JACKETT_URL')
JACKETT_URL = RAW_JACKETT_URL
if RAW_JACKETT_URL:
    import re
    # Fix single slash typos like https:/domain.com
    JACKETT_URL = re.sub(r'^(https?):/([^/])', r'\1://\2', RAW_JACKETT_URL)

JACKETT_API_KEY = os.getenv('JACKETT_API_KEY') or os.getenv('VITE_JACKETT_API_KEY')


# Rate Limiting Store (IP -> last_request_time)
rate_limit_store = {}
ADD_COOLDOWN = 30  # seconds

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def init_pikpak():
    global pikpak_client
    if not PIKPAK_EMAIL or not PIKPAK_PASSWORD:
        print("❌ PIKPAK_EMAIL or PIKPAK_PASSWORD not set in .env")
        return
    
    try:
        print(f"🔄 Logging into PikPak as {PIKPAK_EMAIL}...", file=sys.stderr, flush=True)
        client = PikPakApi(username=PIKPAK_EMAIL, password=PIKPAK_PASSWORD)
        await client.login()
        pikpak_client = client
        print("✅ PikPak Authentication Successful", file=sys.stderr, flush=True)
    except Exception as e:
        error_msg = str(e)
        if "result:review" in error_msg or "review" in error_msg.lower():
            print(f"⚠️ ACTION REQUIRED: PikPak account {PIKPAK_EMAIL} needs verification.", file=sys.stderr, flush=True)
            print(f"⚠️ Please log in to https://mypikpak.com once in your browser to 'trust' this device.", file=sys.stderr, flush=True)
            # We don't set pikpak_client so require_auth can catch it
        
        print(f"❌ PikPak Login Failed for {PIKPAK_EMAIL}", file=sys.stderr, flush=True)
        print(f"❌ Error Detail: {error_msg}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()

# Initialize on startup
with app.app_context():
    run_async(init_pikpak())

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        global pikpak_client
        if not pikpak_client:
            print("🔄 Auth missing, attempting self-healing login...", file=sys.stderr)
            run_async(init_pikpak())
            
        if not pikpak_client:
            # Check if it was a review error
            return jsonify({
                'error': 'Cloud backend not authenticated.',
                'action_required': 'security_verification',
                'message': 'PikPak is requesting security verification. Please log in to https://mypikpak.com once in your browser, then try again here.'
            }), 503
        return f(*args, **kwargs)
    return decorated

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        if ip in rate_limit_store:
            last_time = rate_limit_store[ip]
            if now - last_time < ADD_COOLDOWN:
                remaining = int(ADD_COOLDOWN - (now - last_time))
                return jsonify({'error': f'Rate limit exceeded. Please wait {remaining}s'}), 429
        
        rate_limit_store[ip] = now
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

import sys

@app.route('/api/debug', methods=['GET'])
def debug_config():
    internal_test = "Not tested"
    indexers_found = []
    
    # Try to reach Jackett internally
    try:
        # Test 1: Connectivity
        resp = requests.get(
            f"http://jackett:9117/api/v2.0/indexers/all/results?apikey={JACKETT_API_KEY or ''}&Query=test", 
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=5, verify=False
        )
        internal_test = f"Connected (Status: {resp.status_code})"
        
        # Test 2: Indexer list
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
        'pikpak_auth': bool(pikpak_client),
        'pikpak_env_email': PIKPAK_EMAIL[:3] + "..." if PIKPAK_EMAIL else "MISSING",
        'pikpak_env_pass_set': bool(PIKPAK_PASSWORD),
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
    import re
    import unicodedata
    
    # Step 1: Normalize unicode characters (convert accented chars like é to e)
    query = unicodedata.normalize('NFKD', query).encode('ascii', 'ignore').decode('ascii')
    
    # Step 2: Replace common filename separators with spaces
    query = re.sub(r'[._\-]+', ' ', query)
    
    # Step 3: Remove most special characters but keep alphanumeric, spaces, and colons (:)
    # Colons are useful for series notation like "Show: S01E05"
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
                    # verify=False helps with self-signed certs inside docker networks
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                    response = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            data = enrich_results(data)
                            results = data.get('Results', [])
                            
                            # Strict Category Filtering (Post-Fetch)
                            # Jackett sometimes returns broad matches. We strictly filter if a specific ID was requested.
                            if category and category != 'all':
                                try:
                                    # Safe conversion to int for comparison (Jackett uses int IDs, frontend sends string)
                                    target_cat = int(category)
                                    
                                    # Filter logic that handles both single int and list of ints
                                    filtered_results = []
                                    for r in results:
                                        cat = r.get('Category', [])
                                        # Normalize to list
                                        if isinstance(cat, (int, str)):
                                            cat_list = [int(cat)]
                                        elif isinstance(cat, list):
                                            cat_list = [int(c) for c in cat if str(c).isdigit()]
                                        else:
                                            continue # Unknown format, skip or keep? Skip to be safe/strict as requested.

                                        # Check if target category is in the list
                                        # Also allow sub-category logic? e.g. if we want 2000, 2040 (Movies HD) is ok.
                                        # If user selected 2000 (Movies), we want to show 2000, 2010, 2020 etc.
                                        # So if ANY category in the list starts with the target prefix (first 2 digits)
                                        target_prefix = str(target_cat)[0:2]
                                        
                                        match = False
                                        for c in cat_list:
                                            # Exact match
                                            if c == target_cat:
                                                match = True
                                                break
                                            # Prefix match (only if target is a "parent" category like 2000, 5000)
                                            # If target is specific like 2040, we don't want 2000.
                                            # Simple heuristic: If target ends in 00, it's a parent.
                                            if str(target_cat).endswith('00') and str(c).startswith(target_prefix):
                                                match = True
                                                break
                                        
                                        if match:
                                            filtered_results.append(r)
                                            
                                    results = filtered_results
                                except Exception as filter_e:
                                    print(f"⚠️ Category filter error: {filter_e}", file=sys.stderr)
                                    pass # Ignore filter on error to avoid empty results due to bug

                            # Update data with filtered results
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

@app.route('/api/user', methods=['GET'])
def get_user():
    if not pikpak_client:
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        user_info = pikpak_client.get_user_info()
        return jsonify({
            'username': user_info.get('username'),
            'user_id': user_info.get('user_id')
        })
    except:
        return jsonify({'error': 'Session expired'}), 401

@app.route('/api/download', methods=['POST'])
@require_auth
@rate_limit
def add_download():
    data = request.json
    magnet_url = data.get('url')
    name = data.get('name')
    
    print(f"📥 Adding to Cloud: {name}", file=sys.stderr, flush=True)
    print(f"🔗 URL: {magnet_url[:60]}...", file=sys.stderr, flush=True)
    
    try:
        result = run_async(pikpak_client.offline_download(file_url=magnet_url, name=name))
        print(f"✅ PikPak task created: {result.get('task', {}).get('id', 'unknown')}", file=sys.stderr, flush=True)
        return jsonify({'success': True, 'task': result})
    except Exception as e:
        print(f"❌ PikPak task failed: {str(e)}", file=sys.stderr, flush=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
@require_auth
def list_tasks():
    try:
        result = run_async(pikpak_client.offline_list())
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
@require_auth
def list_files():
    parent_id = request.args.get('parent_id')
    try:
        result = run_async(pikpak_client.file_list(parent_id=parent_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proxy/download/<file_id>')
@require_auth
def proxy_download(file_id):
    try:
        download_data = run_async(pikpak_client.get_download_url(file_id=file_id))
        url = download_data.get('web_content_link') or \
              (download_data.get('medias') and download_data['medias'][0].get('link', {}).get('url'))
        
        if not url:
            return "File URL not found", 404
            
        # Get filename for header
        file_info = run_async(pikpak_client.file_get(file_id=file_id))
        filename = file_info.get('name', 'download')
        
        # URL encode filename for Content-Disposition (RFC 5987)
        quoted_filename = urllib.parse.quote(filename)
        
        resp = requests.get(url, stream=True)
        return app.response_class(
            resp.iter_content(chunk_size=1024*1024),
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quoted_filename}',
                'Content-Type': resp.headers.get('Content-Type', 'application/octet-stream')
            }
        )
    except Exception as e:
        return str(e), 500

# Cleanup Job
def cleanup_files():
    if not pikpak_client: return
    try:
        print("🧹 Running cleanup job...", file=sys.stderr, flush=True)
        # Periodic cleanup of tasks can go here
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}", file=sys.stderr, flush=True)

# Keep-Alive Heartbeat
def pikpak_heartbeat():
    global pikpak_client
    if not pikpak_client: return
    try:
        print("💓 Sending PikPak heartbeat...", file=sys.stderr, flush=True)
        # Fetching user info is a lightweight way to keep session active
        pikpak_client.get_user_info()
    except Exception as e:
        print(f"⚠️ Heartbeat failed: {str(e)}. Session might be expired.", file=sys.stderr, flush=True)
        # We don't force a login here to avoid loops, 
        # the next request will trigger self-healing if needed.

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=60)
scheduler.add_job(func=pikpak_heartbeat, trigger="interval", minutes=5)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
