import requests
import sign # Our sign.py module
import sys
import os
import subprocess
import shutil
import glob

ESP_IP = "192.168.0.110" 
BUILD_DIR = "build"

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

def deploy(ip):
    # 0. Build
    build_project()

    # 1. Sign Package
    print("Signing Package...")
    sign.sign_package()
    
    zip_path = "dist/update.zip"
    sig_path = "dist/update.sig"
    
    # 2. Read Signature
    with open(sig_path, "rb") as f:
        sig_bytes = f.read()
    
    # 3. Read Zip
    with open(zip_path, "rb") as f:
        zip_data = f.read()
        
    print(f"Uploading {len(zip_data)} bytes to http://{ip}/api/ota...")
    
    headers = {
        "X-Signature": sig_bytes.hex()
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
