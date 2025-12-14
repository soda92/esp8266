import ujson
import hashlib
import os
import ubinascii

AUTH_FILE = "auth.json"
SERIAL_FILE = "serial.txt"

def hash_password(password):
    return ubinascii.hexlify(hashlib.sha256(password.encode()).digest()).decode()

def file_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False

def is_setup():
    return file_exists(AUTH_FILE)

def set_password(password):
    p_hash = hash_password(password)
    with open(AUTH_FILE, "w") as f:
        ujson.dump({"hash": p_hash}, f)
    print("Password set.")

def verify_password(password):
    if not is_setup(): return False
    try:
        with open(AUTH_FILE, "r") as f:
            data = ujson.load(f)
        return hash_password(password) == data.get("hash")
    except:
        return False

def get_serial():
    try:
        with open(SERIAL_FILE, "r") as f:
            return f.read().strip()
    except:
        return "UNKNOWN"

def factory_reset(serial_input):
    # If serial matches, delete auth.json and wifi.json
    real_serial = get_serial()
    if serial_input == real_serial:
        try: os.remove(AUTH_FILE)
        except: pass
        try: os.remove("wifi.json")
        except: pass
        return True
    return False
