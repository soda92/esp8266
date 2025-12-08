import os
import sys
import getpass
import keyring
import time
from ampy.pyboard import Pyboard
from ampy.files import Files

# Configuration
SERVICE_ID = "esp8266_weather"
PORT = "/dev/esp8266"
BAUD = 115200

def get_credentials():
    print("Getting WiFi credentials...")
    ssid = keyring.get_password(SERVICE_ID, "ssid")
    password = keyring.get_password(SERVICE_ID, "password")

    if not ssid or not password:
        print("Credentials not found in keyring.")
        ssid = input("Enter WiFi SSID: ")
        password = getpass.getpass("Enter WiFi Password: ")
        
        save = input("Save to keyring? (y/n): ").lower()
        if save == 'y':
            keyring.set_password(SERVICE_ID, "ssid", ssid)
            keyring.set_password(SERVICE_ID, "password", password)
            print("Saved.")
    else:
        print(f"Using credentials for SSID: {ssid}")
        
    return ssid, password

def inject_secrets(file_path, ssid, password):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace placeholders
    new_content = content.replace('WIFI_SSID = "YOUR_WIFI_NAME"', f'WIFI_SSID = "{ssid}"')
    new_content = new_content.replace('WIFI_PASS = "YOUR_WIFI_PASSWORD"', f'WIFI_PASS = "{password}"')
    
    return new_content

def flash_file(board, filename, content=None):
    print(f"Uploading {filename}...")
    files = Files(board)
    
    if content:
        files.put(filename, content.encode('utf-8'))
    else:
        with open(filename, 'rb') as f:
            files.put(filename, f.read())

def main():
    if not os.path.exists(PORT):
        print(f"Error: Device {PORT} not found.")
        return

    ssid, password = get_credentials()
    
    # Prepare board connection
    try:
        pyb = Pyboard(PORT, baudrate=BAUD)
        pyb.enter_raw_repl()
    except Exception as e:
        print(f"Error connecting to board: {e}")
        return

    try:
        # 1. Upload Driver (il3820.py) - no changes needed
        flash_file(pyb, "il3820.py")
        
        # 2. Upload Main (main.py) - with injected secrets
        main_content = inject_secrets("main.py", ssid, password)
        flash_file(pyb, "main.py", content=main_content)
        
        print("Upload complete.")
        
        # 3. Soft Reset to run
        print("Resetting board...")
        pyb.exit_raw_repl()
        pyb.serial.write(b'\x04') # Ctrl-D for Soft Reset
        
        # 4. Monitor Output
        print("--- Serial Output (Ctrl+C to exit) ---")
        while True:
            if pyb.serial.inWaiting() > 0:
                data = pyb.serial.read(pyb.serial.inWaiting())
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        pyb.close()

if __name__ == "__main__":
    main()
