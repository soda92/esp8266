import uos
import machine
import gc
import ubinascii
import hashlib
import hmac

KEYS_DIR = "/keys"
LEGACY_KEY = "secret.key"

def verify_signature(zip_data, signature):
    # 1. Try Keys Directory
    try:
        key_files = uos.listdir(KEYS_DIR)
        for kf in key_files:
            try:
                with open(f"{KEYS_DIR}/{kf}", "r") as f:
                    key_hex = f.read().strip()
                    key = ubinascii.unhexlify(key_hex)
                
                calc_sig = hmac.new(key, zip_data, hashlib.sha256).digest()
                if calc_sig == signature:
                    print(f"Signature Validated by {kf}")
                    return True
            except Exception as e:
                print(f"Key Error {kf}: {e}")
    except OSError:
        pass # Dir doesn't exist

    # 2. Try Legacy Key
    try:
        with open(LEGACY_KEY, "r") as f:
            key_hex = f.read().strip()
            key = ubinascii.unhexlify(key_hex)
        
        calc_sig = hmac.new(key, zip_data, hashlib.sha256).digest()
        if calc_sig == signature:
            print("Signature Validated by Legacy Key")
            return True
    except:
        pass
        
    return False

def verify_and_install(zip_data, signature):
    print("Verifying signature (HMAC-SHA256)...")
    
    if not verify_signature(zip_data, signature):
        print("Verification Failed: No matching key found.")
        return False

    print("Writing update.zip...")
    with open("/update.zip", "wb") as f:
        f.write(zip_data)
    
    print("Unpacking...")
    import unzip
    try:
        unzip.extract("/update.zip", "/")
    except Exception as e:
        print(f"Unzip Failed: {e}")
        return False
    
    print("Update Installed. Rebooting...")
    import uasyncio
    async def reboot_later():
        await uasyncio.sleep(5)
        machine.reset()
    try:
        uasyncio.create_task(reboot_later())
    except:
        machine.reset()
        
    return True