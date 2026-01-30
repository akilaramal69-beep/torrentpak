import os
import asyncio
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from pikpakapi import PikPakApi
from dotenv import load_dotenv
import requests
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
JACKETT_URL = os.getenv('JACKETT_URL')
JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')

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
        if not pikpak_client:
            return jsonify({'error': 'Cloud backend not authenticated. Check .env'}), 503
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

@app.route('/api/search', methods=['GET'])
def search_torrents():
    query = request.args.get('q')
    category = request.args.get('category', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400

    if not JACKETT_URL or not JACKETT_API_KEY:
        print("❌ Search failed: Jackett not configured in .env")
        return jsonify({'error': 'Jackett not configured'}), 500

    try:
        url = f"{JACKETT_URL}/api/v2.0/indexers/all/results"
        params = {
            'apikey': JACKETT_API_KEY,
            'Query': query,
            'Category': category
        }
        print(f"🔍 Searching Jackett: {url} (query: {query})")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Jackett returned error {response.status_code}: {response.text}")
            return jsonify({'error': f'Jackett error: {response.status_code}'}), 502
            
        return jsonify(response.json())
    except Exception as e:
        print(f"❌ Search Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        
        resp = requests.get(url, stream=True)
        return app.response_class(
            resp.iter_content(chunk_size=1024*1024),
            headers={
                'Content-Type': resp.headers.get('Content-Type'),
                'Content-Disposition': f'attachment; filename="{filename}"'
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
