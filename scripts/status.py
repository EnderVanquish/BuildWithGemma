"""Prints the current Argus dashboard state. Usage: python scripts/status.py [url]"""
import json
import sys
import urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"

raw = urllib.request.urlopen(f"{url}/api/stream", timeout=15).readline().decode()
data = json.loads(raw[len("data: "):])

tps = data.get("tokens_per_sec")
print(f"RAM   : {data['ram_used_gb']} / {data['ram_total_gb']} GB  (source: {data['stats_source']})")
print(f"CPU   : {data['cpu_pct']}%   tokens/sec: {round(tps, 2) if tps else '--'}")
print(f"uptime: {data['uptime_seconds']}s   frame_id: {data['frame_id']}")
print(f"\nobservations: {len(data['history'])}")
for i, obs in enumerate(data["history"], 1):
    flag = "UNUSUAL" if obs["unusual"] else "routine"
    print(f"\n{i}. [{obs['timestamp']}] {flag}  severity={obs['severity']}")
    print(f"   obs : {obs['observation']}")
    print(f"   why : {obs['reasoning'][:200]}")
