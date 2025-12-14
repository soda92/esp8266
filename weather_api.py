import usocket
import ujson
import time
import config

# Global Cache
cache = {
    "temp": "--", 
    "desc": "--", 
    "forecast": [], # List of tuples: (DateStr, Max, Min)
    "last_update": 0
}

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
    # Add daily forecast and timezone
    url = f"http://api.open-meteo.com/v1/forecast?latitude={config.LAT}&longitude={config.LON}&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=auto"

    json_str = http_get(url)
    if json_str:
        try:
            data = ujson.loads(json_str)
            
            # 1. Current
            curr = data.get("current_weather", {})
            cache["temp"] = curr.get("temperature", "--")
            code = curr.get("weathercode", 0)
            cache["desc"] = f"Code: {code}"
            
            # 2. Daily Forecast
            daily = data.get("daily", {})
            # daily['time'] is ["2023-10-01", "2023-10-02", ...]
            # daily['temperature_2m_max'] is [22.0, 21.5, ...]
            
            times = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            
            cache["forecast"] = []
            # Get up to 3 days
            for i in range(min(3, len(times))):
                d_str = times[i][5:] # Strip year "2023-10-27" -> "10-27"
                t_max = maxs[i]
                t_min = mins[i]
                cache["forecast"].append((d_str, t_max, t_min))
                
            cache["last_update"] = now
        except Exception as e:
            print(f"Weather Parse Error: {e}")
