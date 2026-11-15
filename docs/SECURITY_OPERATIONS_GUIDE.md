# Quantora Security Configuration & Operations Guide

## 1. Environment Configuration Reference

The platform is configured via environment variables in `.env` or system environment.

| Variable | Default Value | Description | Production Requirement |
|---|---|---|---|
| `APP_ENV` | `development` | Environment mode (`development`, `production`). | Set to `production`. |
| `AUTH_ENABLED` | `false` | Enable JWT and API key authentication. | Set to `true`. |
| `SECRET_KEY` | `quantora-default-dev-secret-key...` | Master HMAC & AES derivation secret (minimum 32 bytes). | **Must be changed** to a strong random key. |
| `ADMIN_API_KEY` | `None` | Static API key for automated operational scripts (`X-API-Key`). | Recommended for monitoring agents. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | JWT access token lifespan in minutes. | Configure per organizational policy. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8000,...` | Comma-separated list of permitted origin URLs. | Set to exact production domain(s). |
| `RATE_LIMIT_PER_MINUTE` | `120` | Default sliding-window rate limit per IP. | Adjust according to traffic load. |

---

## 2. Setting Up Production Authentication

### Step 1: Generate Master Secret Key
Generate a 64-character cryptographic hexadecimal string:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Place in `.env`:
```env
APP_ENV=production
AUTH_ENABLED=true
SECRET_KEY=YOUR_GENERATED_64_CHAR_HEX_KEY
ADMIN_API_KEY=YOUR_GENERATED_ADMIN_KEY
CORS_ALLOWED_ORIGINS=https://quantora.yourdomain.com
```

### Step 2: Register Initial Administrator User
Use the admin registration endpoint or CLI script to provision the root administrator account:
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_GENERATED_ADMIN_KEY" \
  -d '{
    "username": "quant_admin",
    "password": "ReplaceWithSecurePassword123!",
    "role": "admin"
  }'
```

### Step 3: Authenticate and Connect to Protected Endpoints
Obtain an access token:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "quant_admin",
    "password": "ReplaceWithSecurePassword123!"
  }'
```
Response:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "username": "quant_admin",
  "role": "admin"
}
```

Use Bearer token in headers:
```bash
curl -X POST "http://localhost:8000/api/engine/start" \
  -H "Authorization: Bearer eyJhbGciOi..."
```

---

## 3. WebSocket Authentication
To establish a secure connection to `/ws/dashboard`:
```javascript
const token = "YOUR_ACCESS_TOKEN";
const socket = new WebSocket(`ws://localhost:8000/ws/dashboard?token=${encodeURIComponent(token)}`);
```
If `AUTH_ENABLED=true` and no valid token or API key is passed in the query string, the server closes the connection immediately with WebSocket error code `1008` (Policy Violation).
