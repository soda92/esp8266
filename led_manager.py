import machine
import neopixel
import time

# --- LED Configuration ---
# GPIO 0 is Pin D3 on NodeMCU
PIN_LEDS = 0
NUM_LEDS = 4

# Global Brightness Control (0.0 to 1.0)
GLOBAL_BRIGHTNESS = 0.1

led_pin = machine.Pin(PIN_LEDS, machine.Pin.OUT)
pixels = neopixel.NeoPixel(led_pin, NUM_LEDS)

def set_led(r, g, b):
    """
    Set all LEDs with global brightness scaling.
    Inputs (r, g, b) should be 0-255.
    """
    # Apply global brightness scaling
    r = int(r * GLOBAL_BRIGHTNESS)
    g = int(g * GLOBAL_BRIGHTNESS)
    b = int(b * GLOBAL_BRIGHTNESS)
    
    # Clamp to ensure valid range
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    for i in range(NUM_LEDS):
        pixels[i] = (r, g, b)
    pixels.write()

def led_off():
    set_led(0, 0, 0)

def breathe(r, g, b, cycles=1, speed=0.05):
    """
    Fade a color in and out smoothly.
    r, g, b: Target max color (0-255)
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
    led_off()

# --- LED State Functions ---

def led_wifi_wait():
    # Breathe Yellow
    breathe(255, 200, 0, cycles=1, speed=0.02)

def led_wifi_success():
    # Flash Green
    for _ in range(3):
        set_led(0, 255, 0)
        time.sleep(0.1)
        led_off()
        time.sleep(0.1)

def led_wifi_fail():
    set_led(255, 0, 0) # Red

def led_syncing():
    set_led(0, 0, 255) # Blue

def led_heartbeat():
    # Subtle White flash
    set_led(64, 64, 64) 
    time.sleep(0.1)
    led_off()

def led_minute_update():
    # Cyan
    set_led(0, 255, 255)

def led_web_request():
    # Blue
    set_led(0, 0, 255)
