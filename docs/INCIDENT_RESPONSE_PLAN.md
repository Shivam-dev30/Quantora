# Quantora Security Incident Response Plan

## 1. Overview and Purpose
This Incident Response Plan (IRP) defines the procedures for detecting, analyzing, containing, eradicating, and recovering from cybersecurity incidents affecting the Quantora fintech platform.

---

## 2. Incident Classification & Severity Levels

| Severity | Definition | Example Scenarios | Response SLA |
|---|---|---|---|
| **P1 - Critical** | Direct compromise of broker API credentials, unauthorized trading engine control, database compromise, or severe remote code execution. | Leaked Angel One / Delta Exchange API keys, mass unauthorized alert injections, active credential stuffing attacking admin accounts. | **< 15 minutes** |
| **P2 - High** | Denial of service against real-time WebSocket feeds, partial authentication bypass, or rate limiter failure under attack. | Exhaustion of dashboard WebSocket pool, repeated failed brute force attempts against administrative endpoints. | **< 1 hour** |
| **P3 - Medium** | Non-exploitable vulnerability discovery, transient logging error, or misconfigured non-sensitive notification channel. | Misconfigured CORS on development endpoint, expired SMTP credentials for email alerts. | **< 8 hours** |
| **P4 - Low** | Low-risk policy deviation, minor documentation discrepancy, or benign scan activity. | Port scans blocked by perimeter firewall. | **Next business day** |

---

## 3. Incident Response Lifecycle

### Phase 1: Preparation
- Ensure `SECRET_KEY` and `ADMIN_API_KEY` are backed up securely in a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager).
- Maintain immutable backups of `market_alerts.db` and configuration files (`default_config.yaml`).
- Verify automated alerting for `AUTH_LOGIN_FAILED` spikes in `SystemEventModel`.

### Phase 2: Identification & Triage
1. Review recent security events:
   ```sql
   SELECT * FROM system_events WHERE event_type LIKE 'AUTH_%' OR severity IN ('WARNING', 'CRITICAL') ORDER BY created_at DESC LIMIT 50;
   ```
2. Verify system health and active connections at `/health` and `/status`.
3. Check application logs for anomalies or unhandled exceptions.

### Phase 3: Containment
1. **Immediate Engine Pause**: If unauthorized actions are suspected, pause the engine immediately:
   ```bash
   curl -X POST "http://localhost:8000/api/engine/stop" -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```
2. **Credential Revocation & Rotation**:
   - Rotate broker API keys in Angel One SmartAPI and Delta Exchange portals immediately.
   - Rotate `SECRET_KEY` in `.env` to instantly invalidate all active JWT tokens.
   - Rotate administrative user API keys via `/api/auth/api-key/rotate`.
3. **Network Isolation**: Block attacking IP addresses at the perimeter firewall / reverse proxy (Nginx / Cloudflare).

### Phase 4: Eradication
- Identify the root cause (e.g. leaked API key, compromised credential).
- Ensure compromised user accounts are deactivated:
  ```sql
  UPDATE users SET is_active = 0 WHERE username = '<compromised_username>';
  ```
- Purge any unauthorized signals or alerts injected during the event window.

### Phase 5: Recovery
- Restart platform services with rotated credentials and updated security rules.
- Verify engine resumes cleanly:
  ```bash
  curl -X POST "http://localhost:8000/api/engine/start" -H "Authorization: Bearer <NEW_ADMIN_TOKEN>"
  ```
- Run the full automated test suite to confirm platform integrity:
  ```bash
  python -m pytest backend/tests -v
  ```

### Phase 6: Post-Incident Review
- Document incident timeline, root cause, impact, and remediation steps.
- Update security rules, rate limit thresholds, and input validation schemas as needed.
