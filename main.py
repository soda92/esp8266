import machine
import framebuf
import il3820
import time
import network
import ujson
import usocket
import ntptime

# --- USER CONFIGURATION ---
WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

UTC_OFFSET = 28800 

# --- Hardware Setup ---
spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0)
cs = machine.Pin(15, machine.Pin.OUT)
dc = machine.Pin(4, machine.Pin.OUT)
busy = machine.Pin(5, machine.Pin.IN)

epd = il3820.EPD(spi, cs, dc, busy, rst=None)

# Global Weather Cache
weather_cache = {"temp": "--", "desc": "--", "last_update": 0}

def connect_wifi():
    print("Connecting to WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
            print(".")
            
    if wlan.isconnected():
        print(f"Connected! IP: {wlan.ifconfig()[0]}")
        return True
    else:
        print("WiFi Connection Failed")
        return False

def sync_time():
    print("Syncing Time...")
    try:
        ntptime.settime() 
        print("Time Synced.")
    except Exception as e:
        print(f"NTP Error: {e}")

def get_local_time():
    now = time.time() + UTC_OFFSET
    tm = time.localtime(now)
    # Return (HH:MM, YYYY-MM-DD, seconds)
    return "{:02d}:{:02d}".format(tm[3], tm[4]), "{}-{:02d}-{:02d}".format(tm[0], tm[1], tm[2]), tm[5]

def http_get(url):
    try:
        _, _, host, path = url.split('/', 3)
        if not path: path = ""
        
        addr = usocket.getaddrinfo(host, 80)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(addr)
        
        request = f"GET /{path} HTTP/1.0\r\nHost: {host}\r\nUser-Agent: ESP8266\r\n\r\n"
        s.write(request.encode())
        
        response = b""
        while True:
            data = s.read(1024)
            if not data: break
            response += data
        s.close()
        
        headers, body = response.split(b"\r\n\r\n", 1)
        return body.decode('utf-8')
    except Exception as e:
        print(f"HTTP Error: {e}")
        return None

def update_weather():
    # Only update if 15 minutes have passed
    now = time.time()
    if now - weather_cache["last_update"] < 900: # 15 mins
        return

    print("Updating Weather...")
    url = "http://api.open-meteo.com/v1/forecast?latitude=39.90&longitude=116.40&current_weather=true"
    
    json_str = http_get(url)
    if json_str:
        try:
            data = ujson.loads(json_str)
            curr = data.get('current_weather', {})
            weather_cache["temp"] = curr.get('temperature', "--")
            code = curr.get('weathercode', 0)
            weather_cache["desc"] = f"Code: {code}"
            weather_cache["last_update"] = now
        except Exception as e:
            print(f"Weather Parse Error: {e}")

def draw_screen(time_str, date_str):
    print(f"Drawing: {time_str}")
    buf = bytearray(128 * 296 // 8)
    fb = framebuf.FrameBuffer(buf, 128, 296, framebuf.MONO_HLSB)
    fb.fill(0xFF) 
    
    # Top Bar (Date)
    fb.fill_rect(0, 0, 128, 24, 0x00)
    fb.text(date_str, 25, 8, 0xFF)
    
    # Big Time
    fb.text(time_str, 30, 50, 0x00)
    fb.text(time_str, 31, 50, 0x00) 
    
    # Weather
    fb.rect(10, 80, 108, 60, 0x00)
    fb.text("Beijing", 15, 90, 0x00)
    fb.text(f"{weather_cache['temp']} C", 15, 105, 0x00)
    fb.text(str(weather_cache['desc']), 15, 120, 0x00)
    
    epd._command(0x4E, bytearray([0x00]))
    epd._command(0x4F, bytearray([0x00, 0x00]))
    epd.set_frame_memory(buf)
    epd.display_frame()

def main():
    print("Init...")
    epd.init()
    
    if connect_wifi():
        sync_time()
        update_weather()
    
    # Initial Draw
    time_str, date_str, _ = get_local_time()
    draw_screen(time_str, date_str)
    
    last_time_str = time_str

    while True:
        # Check time every 5 seconds
        time.sleep(5)
        
        t_str, d_str, sec = get_local_time()
        
        if t_str != last_time_str:
            # New minute!
            last_time_str = t_str
            
            # Periodically re-sync weather/time
            update_weather()
            
            draw_screen(t_str, d_str)

if __name__ == "__main__":
    main()