import os
import shutil
import zipfile
import hmac
import hashlib

BUILD_DIR = "build"
DIST_DIR = "dist"
KEY_FILE = "secret.key"

def sign_package():
    if not os.path.exists(KEY_FILE):
        print("Error: secret.key not found.")
        return

    if not os.path.exists(BUILD_DIR):
        print("Error: build/ not found.")
        return

    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

    zip_path = os.path.join(DIST_DIR, "update.zip")
    sig_path = os.path.join(DIST_DIR, "update.sig")

    print("Zipping build directory (No Compression)...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, BUILD_DIR)
                zf.write(file_path, arcname)

    print("Signing update.zip (HMAC-SHA256)...")
    with open(KEY_FILE, "r") as f:
        key_hex = f.read().strip()
        key = bytes.fromhex(key_hex)

    with open(zip_path, "rb") as f:
        data = f.read()

    signature = hmac.new(key, data, hashlib.sha256).digest()

    with open(sig_path, "wb") as f:
        f.write(signature)

    print(f"Success! Sig: {signature.hex()}")

if __name__ == "__main__":
    sign_package()