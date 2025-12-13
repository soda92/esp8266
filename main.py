import machine
import framebuf
import il3820
import time
import network
import ujson
import usocket
import ntptime
import neopixel

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

# --- LED Configuration ---
# GPIO 0 is Pin D3 on NodeMCU
PIN_LEDS = 0
NUM_LEDS = 4
led_pin = machine.Pin(PIN_LEDS, machine.Pin.OUT)
pixels = neopixel.NeoPixel(led_pin, NUM_LEDS)


def set_led(r, g, b):
    """Set all 4 LEDs to a specific color instantly."""
    for i in range(NUM_LEDS):
        pixels[i] = (r, g, b)
    pixels.write()


def breathe(r, g, b, cycles=1, speed=0.05):
    """
    Fade a color in and out smoothly.
    r, g, b: Max brightness (0-255)
    cycles: How many times to breathe
    speed: Delay between steps (lower is faster)
    """
    for _ in range(cycles):
        # Fade In
        for i in range(0, 101, 5):  # 0% to 100%
            factor = i / 100
            set_led(int(r * factor), int(g * factor), int(b * factor))
            time.sleep(speed)
        # Fade Out
        for i in range(100, -1, -5):  # 100% to 0%
            factor = i / 100
            set_led(int(r * factor), int(g * factor), int(b * factor))
            time.sleep(speed)


# Global Weather Cache
weather_cache = {"temp": "--", "desc": "--", "last_update": 0}


def connect_wifi():
    print("Connecting to WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)

        # Wait up to 20 seconds, breathing Yellow
        for _ in range(20):
            if wlan.isconnected():
                break
            # Breathe Yellow while waiting (approx 1 sec per cycle)
            breathe(20, 20, 0, cycles=1, speed=0.02)
            print(".")

    if wlan.isconnected():
        print(f"Connected! IP: {wlan.ifconfig()[0]}")
        # Flash Green 3 times to indicate success
        for _ in range(3):
            set_led(0, 50, 0)
            time.sleep(0.1)
            set_led(0, 0, 0)
            time.sleep(0.1)
        return True
    else:
        print("WiFi Connection Failed")
        set_led(50, 0, 0)  # Solid Red for failure
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
    return (
        "{:02d}:{:02d}".format(tm[3], tm[4]),
        "{}-{:02d}-{:02d}".format(tm[0], tm[1], tm[2]),
        tm[5],
    )


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
        s.write(request.encode())  # type: ignore

        response = b""
        while True:
            data = s.read(1024)  # type: ignore
            if not data:
                break
            response += data
        s.close()

        headers, body = response.split(b"\r\n\r\n", 1)
        return body.decode("utf-8")
    except Exception as e:
        print(f"HTTP Error: {e}")
        return None


def update_weather():
    # Only update if 15 minutes have passed
    now = time.time()
    if now - weather_cache["last_update"] < 900:  # 15 mins
        return

    print("Updating Weather...")
    url = "http://api.open-meteo.com/v1/forecast?latitude=39.90&longitude=116.40&current_weather=true"

    json_str = http_get(url)
    if json_str:
        try:
            data = ujson.loads(json_str)
            curr = data.get("current_weather", {})
            weather_cache["temp"] = curr.get("temperature", "--")
            code = curr.get("weathercode", 0)
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
    fb.text(str(weather_cache["desc"]), 15, 120, 0x00)

    epd._command(0x4E, bytearray([0x00]))
    epd._command(0x4F, bytearray([0x00, 0x00]))
    epd.set_frame_memory(buf)
    epd.display_frame()


def main():
    print("Init...")
    epd.init()

    # Try to connect (will breathe yellow)
    if connect_wifi():
        set_led(0, 0, 50)  # Blue while initial syncing
        sync_time()
        update_weather()
        set_led(0, 0, 0)  # Off

    # Initial Draw
    time_str, date_str, _ = get_local_time()
    draw_screen(time_str, date_str)

    last_time_str = time_str

    while True:
        # --- LOOP REACTION: Heartbeat ---
        # Every 5 seconds, flash very dim white briefly
        # This tells you the board hasn't crashed.
        set_led(2, 2, 2)
        time.sleep(0.1)
        set_led(0, 0, 0)

        # Sleep the rest of the 5 seconds
        time.sleep(4.9)

        t_str, d_str, sec = get_local_time()

        if t_str != last_time_str:
            # --- LOOP REACTION: Update Start ---
            # Minute changed! Turn on Dim Cyan
            set_led(0, 10, 10)

            last_time_str = t_str

            # If weather updates, it might take longer, so turn Blue
            if time.time() - weather_cache["last_update"] >= 900:
                set_led(0, 0, 20)  # Blue for web request

            update_weather()
            draw_screen(t_str, d_str)

            # --- LOOP REACTION: Update Done ---
            set_led(0, 0, 0)  # Turn off LEDs


if __name__ == "__main__":
    main()
