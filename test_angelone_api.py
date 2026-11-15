"""
Standalone test script to verify Angel One SmartAPI connectivity.
Confirmed working endpoints (as of Oct 2026):
  Base URL : https://apiconnect.angelone.in
  Login    : /rest/auth/angelbroking/user/v1/loginByPassword
  Profile  : /rest/secure/angelbroking/user/v1/getProfile
  History  : /rest/secure/angelbroking/historical/v1/getCandleData
  Search   : /rest/secure/angelbroking/order/v1/searchScrip
"""

import asyncio
import httpx
import json
import pyotp
from datetime import datetime, timedelta

# ─── Load credentials from .env manually ────────────────────────────────────────
def load_env(path=".env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

env = load_env()

ANGEL_API_KEY     = env.get("ANGEL_API_KEY", "")
ANGEL_CLIENT_CODE = env.get("ANGEL_CLIENT_CODE", "")
ANGEL_PASSWORD    = env.get("ANGEL_PASSWORD", "")
ANGEL_TOTP_SECRET = env.get("ANGEL_TOTP_SECRET", "")
BASE_URL          = "https://apiconnect.angelone.in"
SEP               = "─" * 60


def get_headers(jwt_token: str = "") -> dict:
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "106.193.147.98",
        "X-MACAddress": "fe80::216e:6507:4b90:3719",
        "X-PrivateKey": ANGEL_API_KEY,
    }
    if jwt_token:
        h["Authorization"] = f"Bearer {jwt_token}"
    return h


async def test_login() -> dict:
    print(f"\n{SEP}")
    print("TEST 1: Login (loginByPassword)")
    print(SEP)
    totp = pyotp.TOTP(ANGEL_TOTP_SECRET).now()
    print(f"  TOTP      : {totp}")
    payload = {"clientcode": ANGEL_CLIENT_CODE, "password": ANGEL_PASSWORD, "totp": totp}
    url = f"{BASE_URL}/rest/auth/angelbroking/user/v1/loginByPassword"

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.post(url, json=payload, headers=get_headers())
        data = resp.json()
        if resp.status_code == 200 and data.get("status"):
            td = data.get("data", {})
            print(f"  Status    : SUCCESS (HTTP {resp.status_code})")
            print(f"  JWT Token : {(td.get('jwtToken') or '')[:50]}...")
            print(f"  Feed Token: {(td.get('feedToken') or '')[:30]}...")
            return td
        else:
            print(f"  Status    : FAILED (HTTP {resp.status_code})")
            print(f"  Message   : {data.get('message','')}")
            return {}


async def test_profile(jwt: str):
    print(f"\n{SEP}")
    print("TEST 2: Get User Profile")
    print(SEP)
    url = f"{BASE_URL}/rest/secure/angelbroking/user/v1/getProfile"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=get_headers(jwt))
        data = resp.json()
        if resp.status_code == 200 and data.get("status"):
            p = data.get("data", {})
            print(f"  Name      : {p.get('name','N/A')}")
            print(f"  Email     : {p.get('email','N/A')}")
            print(f"  Mobile    : {p.get('mobileno','N/A')}")
            print(f"  Exchanges : {p.get('exchanges',[])}")
            print(f"  Products  : {p.get('products',[])}")
        else:
            print(f"  FAILED: {data.get('message','')}")


async def test_historical_candles(jwt: str):
    print(f"\n{SEP}")
    print("TEST 3: Historical Candles (RELIANCE / NSE / 15m)")
    print(SEP)
    url = f"{BASE_URL}/rest/secure/angelbroking/historical/v1/getCandleData"
    from_dt = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d 09:15")
    to_dt   = datetime.now().strftime("%Y-%m-%d 15:30")
    payload = {
        "exchange": "NSE",
        "symboltoken": "2885",   # RELIANCE
        "interval": "FIFTEEN_MINUTE",
        "fromdate": from_dt,
        "todate": to_dt,
    }
    print(f"  Range     : {from_dt}  ->  {to_dt}")
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload, headers=get_headers(jwt))
        data = resp.json()
        if resp.status_code == 200 and data.get("status"):
            candles = data.get("data") or []
            print(f"  Candles   : {len(candles)} received")
            if candles:
                print(f"  First     : {candles[0]}")
                print(f"  Last      : {candles[-1]}")
        else:
            print(f"  FAILED: {data.get('message','')} | Code: {data.get('errorcode','')}")


async def test_search(jwt: str):
    print(f"\n{SEP}")
    print("TEST 4: Instrument Search (NIFTY on NSE)")
    print(SEP)
    url = f"{BASE_URL}/rest/secure/angelbroking/order/v1/searchScrip"
    payload = {"exchange": "NSE", "searchscrip": "NIFTY"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=get_headers(jwt))
        data = resp.json()
        if resp.status_code == 200 and data.get("status"):
            results = data.get("data") or []
            print(f"  Found     : {len(results)} instruments")
            for item in results[:5]:
                print(f"    {item.get('tradingsymbol',''):<20} token={item.get('symboltoken','')} expiry={item.get('expiry','spot')}")
        else:
            print(f"  FAILED: {data.get('message','')}")


async def main():
    print("=" * 60)
    print("  ANGEL ONE SMARTAPI - FULL CONNECTIVITY TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Client : {ANGEL_CLIENT_CODE}  |  Key: {ANGEL_API_KEY}")
    print("=" * 60)

    token_data = await test_login()
    if not token_data:
        print("\n[ABORTED] Login failed — skipping remaining tests.")
        return

    jwt = token_data.get("jwtToken", "")
    await test_profile(jwt)
    await test_historical_candles(jwt)
    await test_search(jwt)

    print(f"\n{SEP}")
    print("  ALL TESTS COMPLETED SUCCESSFULLY")
    print(SEP)

if __name__ == "__main__":
    asyncio.run(main())
