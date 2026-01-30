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

## 🚀 All-in-One Deployment (Recommended)

This setup runs **Magnet Cloud**, **Jackett**, and **Caddy** (for SSL) together on your VPS using Docker.

### 1. Clone the repository
```bash
git clone https://github.com/akilaramal69-beep/torrentpak.git
cd torrentpak
```

### 2. Configure Environment
Create a `.env` file from `.env.example`:
```env
PIKPAK_EMAIL=your-email@example.com
PIKPAK_PASSWORD=your-password
JACKETT_API_KEY=your-jackett-api-key # Get this after step 4
DOMAIN=yourdomain.com                 # Your VPS domain/IP
EMAIL=your-email@example.com          # For SSL certificates
```

### 3. Build and Start
```bash
docker-compose up -d --build
```

### 4. Configure Jackett
1. Access Jackett at `http://your-domain/jackett` (or `http://vps-ip:9117` if not proxied).
2. Grab your **API Key** from the top right of the Jackett dashboard.
3. Add your favorite indexers (e.g., 1337x, YTS).
4. **Important**: Update your `.env` with the `JACKETT_API_KEY` and restart with `docker-compose restart app`.

---

## 🛠️ Local Development

### 1. Install Dependencies
```bash
npm install
pip install -r requirements.txt
```

### 2. Build the UI
```bash
npm run build
```

### 3. Start Search Engine
```bash
python app.py
```
Visit `http://localhost:5000`.

---

## 🔒 Security & SSL
*   **Caddy** automatically handles HTTPS for your `DOMAIN` using Let's Encrypt.
*   **Magnet Cloud** runs on port 80/443.
*   **Jackett** is proxied to `/jackett`.
*   To protect your dashboard, consider adding `Basic Auth` in the `Caddyfile`.

