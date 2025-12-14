import uos
import machine
import gc
import ubinascii
import hashlib
import hmac

KEY_FILE = "secret.key"

def verify_and_install(zip_data, signature):
    print("Verifying signature (HMAC-SHA256)...")
    try:
        with open(KEY_FILE, "r") as f:
            key_hex = f.read().strip()
            key = ubinascii.unhexlify(key_hex)
        
        # Calculate HMAC
        # MicroPython hmac.new might handle bytes key/msg
        calc_sig = hmac.new(key, zip_data, hashlib.sha256).digest()
        
        if calc_sig != signature:
            print(f"Sig Mismatch! Calc: {ubinascii.hexlify(calc_sig)}, Recv: {ubinascii.hexlify(signature)}")
            return False
            
        print("Signature Valid!")
    except Exception as e:
        print(f"Verification Error: {e}")
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
        await uasyncio.sleep(2)
        machine.reset()
    try:
        uasyncio.create_task(reboot_later())
    except:
        machine.reset()
        
    return True