import requests
import random

def get_free_proxies():
    try:
        response = requests.get(
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=IN&ssl=all&anonymity=all",
            timeout=10
        )
        proxies = response.text.strip().split("\r\n")
        proxies = [p.strip() for p in proxies if p.strip()]
        print(f"[ProxyFetcher] Loaded {len(proxies)} proxies")
        return proxies
    except Exception as e:
        print(f"[ProxyFetcher] Failed to fetch proxies: {e}")
        return []

def get_random_proxy(proxy_list):
    if not proxy_list:
        return None
    proxy = random.choice(proxy_list)
    return {"http": f"http://{proxy}", "https": f"http://{proxy}"}