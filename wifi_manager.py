import network
import config
import led_manager
import time

def connect():
    print("Connecting to WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(config.WIFI_SSID, config.WIFI_PASS)

        # Wait up to 20 seconds
        for _ in range(20):
            if wlan.isconnected():
                break
            # Visual feedback
            led_manager.led_wifi_wait()
            print(".")

    if wlan.isconnected():
        print(f"Connected! IP: {wlan.ifconfig()[0]}")
        led_manager.led_wifi_success()
        return True
    else:
        print("WiFi Connection Failed")
        led_manager.led_wifi_fail()
        return False
