"""
Debug script: Try both loginByPassword and loginByMPIN on both base URLs.
"""
import asyncio
import httpx
import pyotp
import json

API_KEY     = "8ktherXV"
CLIENT_CODE = "AAAN912947"
PASSWORD    = "1234"        # also used as MPIN
TOTP_SECRET = "2NODGJO5GCUYEIQOSXPEIDP6EU"

HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "106.193.147.98",
    "X-MACAddress": "fe80::216e:6507:4b90:3719",
    "X-PrivateKey": API_KEY,
}

ATTEMPTS = [
    {
        "label": "angelone.in  + loginByMPIN  (NEW preferred)",
        "url": "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByMPIN",
        "payload_key": "mpin",
    },
    {
        "label": "angelbroking.com + loginByMPIN",
        "url": "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/loginByMPIN",
        "payload_key": "mpin",
    },
    {
        "label": "angelone.in  + loginByPassword (legacy)",
        "url": "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword",
        "payload_key": "password",
    },
    {
        "label": "angelbroking.com + loginByPassword (legacy)",
        "url": "https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/loginByPassword",
        "payload_key": "password",
    },
]

async def try_login(label, url, payload_key):
    totp = pyotp.TOTP(TOTP_SECRET).now()
    payload = {
        "clientcode": CLIENT_CODE,
        payload_key: PASSWORD,
        "totp": totp,
    }
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  URL: {url}")
    print(f"  TOTP: {totp}")
    print(f"{'='*60}")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        try:
            resp = await client.post(url, json=payload, headers=HEADERS_BASE)
            print(f"  HTTP {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type','')}")
            print(f"  Body ({len(resp.text)} bytes): {resp.text[:500]}")

            if resp.text.strip():
                try:
                    data = resp.json()
                    if data.get("status"):
                        print(f"\n  >>> LOGIN SUCCESS! <<<")
                        token_data = data.get("data", {})
                        print(f"  JWT: {(token_data.get('jwtToken') or '')[:40]}...")
                        print(f"  Feed: {token_data.get('feedToken','')[:20]}...")
                        return token_data
                    else:
                        print(f"  >>> Login rejected: {data.get('message','')}")
                except Exception:
                    print(f"  >>> Non-JSON response")
            else:
                print(f"  >>> Empty body")
        except Exception as e:
            print(f"  >>> Exception: {e}")
    return None

async def main():
    print("Angel One SmartAPI - Endpoint Discovery Test")
    print(f"Client: {CLIENT_CODE} | API Key: {API_KEY}")

    for attempt in ATTEMPTS:
        result = await try_login(attempt["label"], attempt["url"], attempt["payload_key"])
        if result:
            jwt = result.get("jwtToken", "")
            print(f"\n[SUCCESS] Working endpoint found. JWT obtained.")
            # Test profile with this JWT
            profile_url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getProfile"
            async with httpx.AsyncClient(timeout=15.0) as client:
                h = dict(HEADERS_BASE)
                h["Authorization"] = f"Bearer {jwt}"
                r = await client.get(profile_url, headers=h)
                print(f"\nProfile [{r.status_code}]: {r.text[:300]}")
            break
    else:
        print("\n[FAILED] No endpoint worked. Check:")
        print("  1. Angel One SmartAPI app is ACTIVE at smartapi.angelbroking.com")
        print("  2. TOTP secret matches the one in your Authenticator app")
        print("  3. Password/MPIN is correct")

if __name__ == "__main__":
    asyncio.run(main())
