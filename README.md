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

## 🚀 Deployment Guide (VPS)

### 1. Prerequisites
- A VPS with Docker and Docker Compose installed.
- A [PikPak](https://mypikpak.com) account.
- A [Jackett](https://github.com/Jackett/Jackett) instance running.

### 2. Setup Directory
```bash
mkdir magnet-cloud && cd magnet-cloud
# Copy project files here
```

### 3. Configure Environment
Create a `.env` file:
```env
PIKPAK_EMAIL=your-email@example.com
PIKPAK_PASSWORD=your-password
JACKETT_URL=http://your-jackett-ip:9117
JACKETT_API_KEY=your-jackett-api-key
SECRET_KEY=generate-a-random-string
```

### 4. Build and Run
```bash
docker-compose up -d --build
```
The app will be available at `http://your-vps-ip:5000`.

---

## 🛠️ Local Development

### 1. Install Backend
```bash
pip install -r requirements.txt
python app.py
```

### 2. Install Frontend
```bash
npm install
npm run dev
```

---

## 🔒 Security Note
This application uses a global cloud account defined in the `.env` file. Any user who has access to the web interface can view and download files in that account. Do not share the URL publicly without adding an authentication layer (like Basic Auth or Nginx Proxy Manager auth) if privacy is required.
