import os
import secrets

KEY_FILE = "secret.key"

def generate():
    if os.path.exists(KEY_FILE):
        print(f"Warning: {KEY_FILE} exists.")
        return

    # Generate 32 bytes (256 bits)
    key = secrets.token_hex(32)
    
    with open(KEY_FILE, "w") as f:
        f.write(key)
        
    print(f"Generated {KEY_FILE}: {key}")

if __name__ == "__main__":
    generate()