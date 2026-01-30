import os
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

load_dotenv()

app = Flask(__name__, static_folder='dist', static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'magnet_cloud_secret_shared_key')
CORS(app)

# PikPak Configuration
PIKPAK_EMAIL = os.getenv('PIKPAK_EMAIL')
PIKPAK_PASSWORD = os.getenv('PIKPAK_PASSWORD')

# Jackett Configuration
JACKETT_URL = os.getenv('JACKETT_URL') or os.getenv('VITE_JACKETT_URL')
JACKETT_API_KEY = os.getenv('JACKETT_API_KEY') or os.getenv('VITE_JACKETT_API_KEY')

# Global PikPak Client
pikpak_client = None

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
        print(f"🔄 Logging into PikPak as {PIKPAK_EMAIL}...")
        client = PikPakApi(username=PIKPAK_EMAIL, password=PIKPAK_PASSWORD)
        await client.login()
        pikpak_client = client
        print("✅ PikPak Authentication Successful")
    except Exception as e:
        print(f"❌ PikPak Login Failed: {str(e)}")

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
            return jsonify({'error': 'Cloud backend not authenticated. Please check your PIKPAK_EMAIL and PIKPAK_PASSWORD in the .env file and restart the containers.'}), 503
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
            indexers = idx_resp.json()
            indexers_found = [i.get('name') for i in indexers if i.get('configured')]
    except Exception as e:
        internal_test = f"Failed: {str(e)}"

    return jsonify({
        'jackett_url_env': JACKETT_URL,
        'jackett_key_set': bool(JACKETT_API_KEY),
        'internal_test': internal_test,
        'configured_indexers': indexers_found,
        'indexers_count': len(indexers_found),
        'pikpak_auth': bool(pikpak_client),
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
    
    for res in results:
        magnet = res.get('MagnetUri')
        link = res.get('Link')
        info_hash = res.get('InfoHash')
        
        if not magnet and link and link.startswith('magnet:'):
            magnet = link
            
        if magnet:
            # Add trackers if not present
            sep = '&' if '?' in magnet else '?'
            res['MagnetUri'] = f"{magnet}{sep}{tracker_query}"
        elif info_hash:
            # Construct magnet from hash
            name = urllib.parse.quote(res.get('Title', 'download'))
            res['MagnetUri'] = f"magnet:?xt=urn:btih:{info_hash}&dn={name}&{tracker_query}"
            
    return data

@app.route('/api/search', methods=['GET'])
def search_torrents():
    query = request.args.get('q')
    category = request.args.get('category', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

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
                if category and category != 'all' and category != '':
                    params['Category[]'] = category
                    params['Category'] = category
                    
                print(f"🔍 Trying Jackett: {url} (query: {query})", file=sys.stderr, flush=True)
                # verify=False helps with self-signed certs inside docker networks
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                response = requests.get(url, params=params, headers=headers, timeout=25, verify=False)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        data = enrich_results(data)
                        results = data.get('Results', [])
                        print(f"✅ SUCCESS: Found {len(results)} results using {url}", file=sys.stderr, flush=True)
                        return jsonify(data)
                    except Exception as je:
                        print(f"❌ JSON Parse Error from {url}: {str(je)}", file=sys.stderr, flush=True)
                        last_error = f"JSON Error: {str(je)}"
                        continue
                
                if response.status_code == 404:
                    continue
                
                print(f"⚠️ {url} returned {response.status_code}: {response.text[:200]}", file=sys.stderr, flush=True)
                last_error = f"Jackett error {response.status_code}"
            except Exception as e:
                print(f"⚠️ {url} failed: {str(e)}", file=sys.stderr, flush=True)
                last_error = str(e)

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
    
    try:
        result = run_async(pikpak_client.offline_download(file_url=magnet_url, name=name))
        return jsonify({'success': True, 'task': result})
    except Exception as e:
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
        print("🧹 Running cleanup job...")
        # Implementation of file cleanup based on timestamps
        # Since we use global account, we should be careful what we delete.
        # For simplicity in this white-label version, we focus on tasks.
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_files, trigger="interval", minutes=60)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
