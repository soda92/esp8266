import ntptime
import time
import config

def sync():
    print("Syncing Time...")
    try:
        ntptime.settime()
        print("Time Synced.")
    except Exception as e:
        print(f"NTP Error: {e}")

def get_local_time():
    now = time.time() + config.UTC_OFFSET
    tm = time.localtime(now)
    # Return (HH:MM, YYYY-MM-DD, seconds)
    return (
        "{:02d}:{:02d}".format(tm[3], tm[4]),
        "{}-{:02d}-{:02d}".format(tm[0], tm[1], tm[2]),
        tm[5],
    )
