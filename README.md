# ☁️ Magnet Cloud

A white-labeled, high-performance torrent search and cloud download platform. Search for magnets and download them directly to your private cloud storage.

## ✨ Features
- **Global Search**: Search across dozens of indexers via Jackett.
- **Cloud Downloads**: One-click download to your cloud drive.
- **Proxy Streaming**: Download files via backend proxy to preserve anonymity.
- **Rate Limited**: Built-in IP-based rate limiting to protect the backend.
- **Mobile Friendly**: Fully responsive design.
- **Auto-Auth**: Set credentials in `.env` once; no user login required.

---

## 🛠️ Local Development

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/akilaramal69-beep/torrentpak.git
cd torrentpak
npm install
pip install -r requirements.txt
```

### 2. Build the UI
```bash
npm run build
```

### 3. Setup Environment
Create a `.env` file from `.env.example`:
```env
PIKPAK_EMAIL=your-email@example.com
PIKPAK_PASSWORD=your-password
JACKETT_URL=http://your-jackett-ip:9117
JACKETT_API_KEY=your-jackett-api-key
```

### 4. Start the Server
```bash
python app.py
```
Visit `http://localhost:5000`.

---

## 🚀 VPS Deployment (Docker)

This is the recommended way to deploy for production.

1. **Clone the repo** on your VPS.
2. **Create `.env`** with your credentials.
3. **Build and start**:
```bash
docker-compose up -d --build
```
The app will automatically build the frontend inside the container and serve it via Gunicorn.

---

## 🔒 Security Note
This application uses a global cloud account. Anyone with the URL can view/download files. 
**Recommendation**: Use a reverse proxy (like Nginx) to add a password (Basic Auth) or use Cloudflare Access to protect your instance.

