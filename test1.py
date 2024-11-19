import requests

proxy = {
    "http": "http://127.0.0.1:40002",
    "https": "http://127.0.0.1:40002"
}

try:
    response = requests.get("http://ip-api.com", proxies=proxy, timeout=5)
    if response.status_code == 200:
        print("Proxy works! HTTP Response:", response.status_code)
    else:
        print("Failed! HTTP Response:", response.status_code)
except Exception as e:
    print("Error:", e)
