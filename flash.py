import os
import sys
import subprocess
import shutil
import glob

# Configuration
PORT = "/dev/esp32"
BUILD_DIR = "build"

def prepare_build():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    
    # 0. Generate Keys if needed
    if not os.path.exists("secret.key"):
        print("Generating Keys...")
        subprocess.run([sys.executable, "tools/keygen.py"], check=True)
    
    # 1. Build Frontend
    print("Building Frontend...")
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)
    
    # 2. Copy Source Files
    sources = glob.glob("*.py") + glob.glob("*.json") + ["secret.key"]
    for src in sources:
        if src == os.path.basename(__file__): continue
        shutil.copy(src, os.path.join(BUILD_DIR, src))
        
    # 3. Copy Microdot Lib
    microdot_path = ".venv/lib/python3.13/site-packages/microdot/microdot.py"
    if os.path.exists(microdot_path):
        shutil.copy(microdot_path, os.path.join(BUILD_DIR, "microdot.py"))

    # 4. Copy WWW
    if os.path.exists("www"):
        shutil.copytree("www", os.path.join(BUILD_DIR, "www"))

def main():
    if not os.path.exists(PORT):
        print(f"Error: Device {PORT} not found.")
        return

    print("Preparing Build Directory...")
    import glob # Lazy import
    prepare_build()
    
    print("Compiling Fonts...")
    subprocess.run([sys.executable, "compile_font.py"], cwd=BUILD_DIR, check=True)
    
    print("Uploading with mpremote (Fast)...")
    # Clean up compile_font from build before upload
    if os.path.exists(os.path.join(BUILD_DIR, "compile_font.py")):
        os.remove(os.path.join(BUILD_DIR, "compile_font.py"))

    try:
        # mpremote cp -r build/* :
        # Note: mpremote syntax for recursive copy from local to remote root
        cmd = ["mpremote", "connect", PORT, "cp", "-r", f"{BUILD_DIR}/.", ":"]
        subprocess.run(cmd, check=True)
        
        print("Upload complete.")
        print("Resetting board...")
        subprocess.run(["mpremote", "connect", PORT, "reset"], check=True)
        
        # Monitor
        print("Monitoring...")
        subprocess.run(["mpremote", "connect", PORT, "repl"], check=True)

    except KeyboardInterrupt:
        print("\nExiting...")
    except subprocess.CalledProcessError as e:
        print(f"\nmpremote failed: {e}")

if __name__ == "__main__":
    main()