import usocket
import ujson
import time
import config

# Global Cache
cache = {"temp": "--", "desc": "--", "last_update": 0}

def http_get(url):
    try:
        _, _, host, path = url.split("/", 3)
        if not path:
            path = ""

        addr = usocket.getaddrinfo(host, 80)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(addr)

        request = f"GET /{path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: ESP8266\r\n\r\n"
        s.write(request.encode())

        response = b""
        while True:
            data = s.read(1024)
            if not data:
                break
            response += data
        s.close()

        headers, body = response.split(b"\r\n\r\n", 1)
        return body.decode("utf-8")
    except Exception as e:
        print(f"HTTP Error: {e}")
        return None

def update():
    # Only update if 15 minutes have passed
    now = time.time()
    if now - cache["last_update"] < 900:  # 15 mins
        return

    print("Updating Weather...")
    url = f"http://api.open-meteo.com/v1/forecast?latitude={config.LAT}&longitude={config.LON}&current_weather=true"

    json_str = http_get(url)
    if json_str:
        try:
            data = ujson.loads(json_str)
            curr = data.get("current_weather", {})
            cache["temp"] = curr.get("temperature", "--")
            code = curr.get("weathercode", 0)
            cache["desc"] = f"Code: {code}"
            cache["last_update"] = now
        except Exception as e:
            print(f"Weather Parse Error: {e}")
