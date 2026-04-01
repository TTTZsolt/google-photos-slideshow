import urllib.request
import json

try:
    url = "http://localhost:8080/slideshow/devices"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Response:", data)
except Exception as e:
    print("Error:", e)
