import os
import glob
import sys
import time
import subprocess
import shutil
from ampy.pyboard import Pyboard
from ampy.files import Files

# Configuration
PORT = "/dev/esp32"
BAUD = 115200
BUILD_DIR = "build"

def flash_file(board, local_path, remote_path):
    print(f"Uploading {remote_path}...")
    files = Files(board)
    with open(local_path, "rb") as f:
        files.put(remote_path, f.read())

def compile_file(filepath):
    # filepath is like "build/main.py"
    # output is "build/main.mpy"
    mpy_file = filepath.replace(".py", ".mpy")
    try:
        subprocess.run(["mpy-cross", "-o", mpy_file, filepath], check=True)
        return mpy_file
    except subprocess.CalledProcessError:
        print(f"Error compiling {filepath}")
        return None

def prepare_build():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR)
    
    # Copy files
    sources = glob.glob("*.py") + glob.glob("*.html")
    # Exclude flash.py itself
    myself = os.path.basename(__file__)
    if myself in sources:
        sources.remove(myself)
        
    for src in sources:
        shutil.copy(src, os.path.join(BUILD_DIR, src))
        
    return sources

def clean_board(board, build_files):
    print("Cleaning obsolete files on board...")
    files = Files(board)
    try:
        board_files = files.ls()
        board_files = [f.strip().lstrip("/") for f in board_files] # Normalize names
        
        for local_file in build_files:
            filename = os.path.basename(local_file)
            
            # If we are uploading 'main.mpy', we must remove 'main.py' from board
            if filename.endswith(".mpy"):
                py_version = filename.replace(".mpy", ".py")
                if py_version in board_files:
                    print(f"Removing conflict: {py_version}")
                    try:
                        files.rm(py_version)
                    except:
                        pass

    except Exception as e:
        print(f"Error cleaning board: {e}")

def main():
    if not os.path.exists(PORT):
        print(f"Error: Device {PORT} not found.")
        return

    print("Preparing Build Directory...")
    prepare_build()
    
    # 1. Compile Fonts (inside build dir)
    print("Compiling Fonts...")
    subprocess.run([sys.executable, "compile_font.py"], cwd=BUILD_DIR, check=True)
    
    # 2. Cross Compile Python Files
    print("Cross Compiling to .mpy...")
    build_files_all = glob.glob(os.path.join(BUILD_DIR, "*.py"))
    
    for py_file in build_files_all:
        filename = os.path.basename(py_file)
        if filename == "compile_font.py":
            continue
            
        mpy_path = compile_file(py_file)
        if mpy_path:
            os.remove(py_file)

    # Prepare board connection
    try:
        pyb = Pyboard(PORT, baudrate=BAUD)
        pyb.enter_raw_repl()
    except Exception as e:
        print(f"Error connecting to board: {e}")
        return

    try:
        # Collect files to upload
        files_to_upload = glob.glob(os.path.join(BUILD_DIR, "*"))
        # Add font binary explicitly if glob missed it or just to be sure
        if os.path.exists(os.path.join(BUILD_DIR, "font_data.bin")):
            if os.path.join(BUILD_DIR, "font_data.bin") not in files_to_upload:
                files_to_upload.append(os.path.join(BUILD_DIR, "font_data.bin"))
                
        # Exclude scripts that shouldn't be on the board
        excluded_files = [os.path.basename(__file__), "compile_font.py", "time_manager.py"]
        for f in excluded_files:
            if f in files_to_upload:
                files_to_upload.remove(f)

        # 3. Smart Clean
        clean_board(pyb, files_to_upload)
        
        # 4. Upload
        for local_path in files_to_upload:
            filename = os.path.basename(local_path)
            flash_file(pyb, local_path, filename)

        print("Upload complete.")

        # 4. Soft Reset
        print("Resetting board...")
        pyb.exit_raw_repl()
        pyb.serial.write(b"\x04")  # Ctrl-D for Soft Reset

        # 5. Monitor Output
        print("--- Serial Output (Monitoring for 10s) ---")
        start_time = time.time()
        while time.time() - start_time < 10:
            if pyb.serial.inWaiting() > 0:  # type: ignore
                data = pyb.serial.read(pyb.serial.inWaiting())  # type: ignore
                sys.stdout.write(data.decode("utf-8", errors="replace"))
                sys.stdout.flush()
            time.sleep(0.1)
        print("\nDone.")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        pyb.close()
        # Optional: Cleanup build dir
        # shutil.rmtree(BUILD_DIR)


if __name__ == "__main__":
    main()
