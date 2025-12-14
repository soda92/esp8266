import requests
import sign # Our sign.py module
import sys
import os
import subprocess
import shutil
import glob
import keyring
import getpass

ESP_IP = "192.168.0.110" 
BUILD_DIR = "build"
SERVICE_ID = "esp32_ota"
USERNAME = "admin"

def build_project():
    print("Building Project...")
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    
    # 1. Build Frontend
    print("  Building Frontend...")
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)
    
    # 2. Copy Source Files
    print("  Copying Source...")
    sources = glob.glob("*.py") + glob.glob("*.json") + ["secret.key"]
    for src in sources:
        if src == "flash.py": continue
        shutil.copy(src, os.path.join(BUILD_DIR, src))
        
    # 3. Copy Microdot
    microdot_path = ".venv/lib/python3.13/site-packages/microdot/microdot.py"
    if os.path.exists(microdot_path):
        shutil.copy(microdot_path, os.path.join(BUILD_DIR, "microdot.py"))

    # 4. Copy WWW
    if os.path.exists("www"):
        shutil.copytree("www", os.path.join(BUILD_DIR, "www"))
        
    # 5. Compile Fonts
    print("  Compiling Fonts...")
    subprocess.run([sys.executable, "compile_font.py"], cwd=BUILD_DIR, check=True)

def get_token(ip):
    password = keyring.get_password(SERVICE_ID, USERNAME)
    
    while True:
        if not password:
            password = getpass.getpass(f"Enter Password for {ip}: ")
            
        try:
            r = requests.post(f"http://{ip}/api/auth/login", json={"password": password})
            if r.status_code == 200:
                print("Login Successful.")
                # Save correct password
                keyring.set_password(SERVICE_ID, USERNAME, password)
                return r.json().get("token")
            elif r.status_code == 401:
                print("Invalid Password.")
                password = None # Ask again
            else:
                print(f"Login Error: {r.status_code} - {r.text}")
                return None
        except requests.exceptions.ConnectionError:
            print(f"Could not connect to {ip}")
            return None

def deploy(ip):
    # 0. Auth
    token = get_token(ip)
    if not token:
        return

    # 1. Build
    build_project()

    # 2. Sign Package
    print("Signing Package...")
    sign.sign_package()
    
    zip_path = "dist/update.zip"
    sig_path = "dist/update.sig"
    
    with open(sig_path, "rb") as f:
        sig_bytes = f.read()
    
    with open(zip_path, "rb") as f:
        zip_data = f.read()
        
    print(f"Uploading {len(zip_data)} bytes to http://{ip}/api/ota...")
    
    headers = {
        "X-Signature": sig_bytes.hex(),
        "X-Token": token,
        "Content-Type": "application/octet-stream"
    }
    
    try:
        r = requests.post(f"http://{ip}/api/ota", data=zip_data, headers=headers)
        if r.status_code == 200:
            print("Success! Device is updating.")
        else:
            print(f"Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        deploy(sys.argv[1])
    else:
        deploy(ESP_IP)
