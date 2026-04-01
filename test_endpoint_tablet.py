import urllib.request
import json
import urllib.error

try:
    url = "http://192.168.1.157:8080/slideshow/devices"
    print(f"Requesting {url}...")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Response:", json.dumps(data, indent=2))
except urllib.error.URLError as e:
    print("URL Error:", e)
except Exception as e:
    print("Error:", e)
