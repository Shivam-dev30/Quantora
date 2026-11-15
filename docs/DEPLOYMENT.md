# Production Deployment Guide

## 1. Prerequisites
- Python 3.12+
- Node.js 20+ & npm (for UI builds)
- SQLite (built-in) or PostgreSQL (optional)
- Angel One SmartAPI credentials (API Key, Client Code, Password, TOTP Secret)
- Delta Exchange credentials (API Key & Secret, or public market stream)
- Telegram Bot token & chat ID (recommended for mobile alerts)

---

## 2. Configuration Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your secure credentials:
   ```env
   # Angel One
   ANGEL_API_KEY=your_smartapi_key
   ANGEL_CLIENT_CODE=your_client_code
   ANGEL_PASSWORD=your_password
   ANGEL_TOTP_SECRET=your_base32_totp_secret

   # Telegram
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_CHAT_ID=your_chat_id
   ```
3. Customize monitored assets in `backend/app/config/default_config.yaml`:
   ```yaml
   markets:
     equity:
       enabled: true
       symbols: [RELIANCE, TCS, INFY, HDFCBANK]
     equity_futures:
       enabled: true
       expiry_mode: current
       symbols: [NIFTY, BANKNIFTY]
     commodity:
       enabled: true
       symbols: [CRUDEOIL, GOLD]
     crypto:
       enabled: true
       symbols: [BTCUSD, ETHUSD]
   ```

---

## 3. Running Locally (Development Mode)

### Start Backend:
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend (Vite Dev Server):
```bash
cd frontend
npm run dev
```
The terminal UI will be available at `http://localhost:5173` with real-time WebSocket connectivity to backend port `8000`.

---

## 4. Running in Production with Docker Compose

Build and launch the complete stack:
```bash
docker compose up -d --build
```
Check container logs:
```bash
docker compose logs -f
```
Open `http://localhost:8000` in your browser to access the combined API and Terminal Dashboard.

---

## 5. Running as a Linux Systemd Service

Create `/etc/systemd/system/market-alerts.service`:
```ini
[Unit]
Description=Multi-Asset Market Alert Platform
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/market-alert-system
ExecStart=/opt/market-alert-system/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/opt/market-alert-system/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable market-alerts
sudo systemctl start market-alerts
```
