import os
import glob
import sys
import getpass
import keyring
import time
import subprocess
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
        if save == "y":
            keyring.set_password(SERVICE_ID, "ssid", ssid)
            keyring.set_password(SERVICE_ID, "password", password)
            print("Saved.")
    else:
        print(f"Using credentials for SSID: {ssid}")

    return ssid, password


def inject_secrets(content, ssid, password):
    # Replace placeholders
    new_content = content.replace(
        'WIFI_SSID = "YOUR_WIFI_NAME"', f'WIFI_SSID = "{ssid}"'
    )
    new_content = new_content.replace(
        'WIFI_PASS = "YOUR_WIFI_PASSWORD"', f'WIFI_PASS = "{password}"'
    )
    return new_content


def flash_file(board, filename, content=None):
    print(f"Uploading {filename}...")
    files = Files(board)

    if content:
        files.put(filename, content.encode("utf-8"))
    else:
        with open(filename, "rb") as f:
            files.put(filename, f.read())


def main():
    if not os.path.exists(PORT):
        print(f"Error: Device {PORT} not found.")
        return

    # Compile Fonts First
    print("Compiling Fonts...")
    subprocess.run([sys.executable, "compile_font.py"], check=True)

    ssid, password = get_credentials()

    # Prepare board connection
    try:
        pyb = Pyboard(PORT, baudrate=BAUD)
        pyb.enter_raw_repl()
    except Exception as e:
        print(f"Error connecting to board: {e}")
        return

    try:
        # Get all .py files
        files_to_upload = glob.glob("*.py")
        
        # Add index.html if it exists
        if os.path.exists("index.html"):
            files_to_upload.append("index.html")
        
        # Exclude scripts that shouldn't be on the board
        excluded_files = [os.path.basename(__file__), "compile_font.py"]
        for f in excluded_files:
            if f in files_to_upload:
                files_to_upload.remove(f)

        for filename in files_to_upload:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Inject secrets into config.py (or main.py for backward compat if config.py doesn't exist yet)
            if filename == "config.py" or (filename == "main.py" and "WIFI_SSID =" in content):
                content = inject_secrets(content, ssid, password)
                flash_file(pyb, filename, content=content)
            else:
                flash_file(pyb, filename)

        print("Upload complete.")

        # 3. Soft Reset to run
        print("Resetting board...")
        pyb.exit_raw_repl()
        pyb.serial.write(b"\x04")  # Ctrl-D for Soft Reset

        # 4. Monitor Output
        print("--- Serial Output (Ctrl+C to exit) ---")
        while True:
            if pyb.serial.inWaiting() > 0:  # type: ignore
                data = pyb.serial.read(pyb.serial.inWaiting())  # type: ignore
                sys.stdout.write(data.decode("utf-8", errors="replace"))
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
