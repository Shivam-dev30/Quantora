"""Fetch ALL products from Delta Exchange - no filter, full pagination."""
import httpx, json

BASE = "https://api.delta.exchange/v2"

all_products = []
after = None
page = 0
while True:
    params = {"limit": 100}
    if after:
        params["after"] = after
    r = httpx.get(f"{BASE}/products", params=params, timeout=30)
    data = r.json()
    batch = data.get("result", [])
    page += 1
    print(f"Page {page}: got {len(batch)} products (total so far: {len(all_products)+len(batch)})")
    if not batch:
        break
    all_products.extend(batch)
    meta = data.get("meta", {})
    after = meta.get("after")
    if not after or len(batch) < 100:
        break

print(f"\nGrand Total products: {len(all_products)}")

# Count by type and state
from collections import Counter
by_type  = Counter(p.get("contract_type","unknown") for p in all_products)
by_state = Counter(p.get("state","unknown") for p in all_products)
print("\nBy contract_type:")
for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {k:<35}: {v}")
print("\nBy state:")
for k, v in sorted(by_state.items(), key=lambda x: -x[1]):
    print(f"  {k:<20}: {v}")

# Filter only LIVE futures (perp + expiry)
live_futures = [
    p for p in all_products
    if p.get("state") == "live"
    and p.get("contract_type") in (
        "perpetual_futures", "futures", "move_options",
        "interest_rate_swaps", "spreads"
    )
]

# Perpetual futures only (the most tradeable)
live_perp = [p for p in all_products
             if p.get("state") == "live"
             and p.get("contract_type") == "perpetual_futures"]

live_expiry = [p for p in all_products
               if p.get("state") == "live"
               and p.get("contract_type") == "futures"]

print(f"\nLive Perpetual Futures: {len(live_perp)}")
print(f"Live Expiry Futures   : {len(live_expiry)}")

print("\n=== ALL LIVE PERPETUAL FUTURES ===")
for p in sorted(live_perp, key=lambda x: x.get("symbol","")):
    print(f"  ID={p.get('id'):<8} sym={p.get('symbol',''):<30} quote={p.get('quoting_asset',{}).get('symbol','')}")

print("\n=== ALL LIVE EXPIRY FUTURES ===")
for p in sorted(live_expiry, key=lambda x: x.get("symbol","")):
    print(f"  ID={p.get('id'):<8} sym={p.get('symbol',''):<35}")

# Save
with open("delta_products_all.json","w") as f:
    json.dump(all_products, f, indent=2)
print(f"\nSaved ALL {len(all_products)} products to delta_products_all.json")
