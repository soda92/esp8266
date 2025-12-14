import machine
import time
import il3820
import wifi_manager
import time_manager
import weather_api
import display_ui
import led_manager

# --- Hardware Setup ---
spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0)
cs = machine.Pin(15, machine.Pin.OUT)
dc = machine.Pin(4, machine.Pin.OUT)
busy = machine.Pin(5, machine.Pin.IN)

epd = il3820.EPD(spi, cs, dc, busy, rst=None)

def main():
    print("Init System...")
    epd.init()

    # Try to connect
    if wifi_manager.connect():
        led_manager.led_syncing()
        time_manager.sync()
        weather_api.update()
        led_manager.led_off()

    # Initial Draw
    time_str, date_str, _ = time_manager.get_local_time()
    display_ui.draw_screen(epd, time_str, date_str)

    last_time_str = time_str

    while True:
        # --- LOOP REACTION: Heartbeat ---
        led_manager.led_heartbeat()

        # Sleep the rest of the 5 seconds
        time.sleep(4.9)

        t_str, d_str, sec = time_manager.get_local_time()

        if t_str != last_time_str:
            # --- LOOP REACTION: Update Start ---
            led_manager.led_minute_update()

            last_time_str = t_str

            # If weather updates, it might take longer
            if time.time() - weather_api.cache["last_update"] >= 900:
                led_manager.led_web_request()

            weather_api.update()
            display_ui.draw_screen(epd, t_str, d_str)

            # --- LOOP REACTION: Update Done ---
            led_manager.led_off()

if __name__ == "__main__":
    main()