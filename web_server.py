import uasyncio
import os
import ujson
import led_manager

# Global State
custom_message = ""

async def send_response(writer, code, content_type, body):
    header = f"HTTP/1.1 {code}\r\nContent-Type: {content_type}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    await writer.awrite(header.encode())
    await writer.awrite(body)

async def handle_client(reader, writer):
    global custom_message
    try:
        # 1. Read Request Line
        request_line = await reader.readline()
        if not request_line:
            writer.close()
            await writer.wait_closed()
            return
            
        req_str = request_line.decode('utf-8').strip()
        try:
            method, path, _ = req_str.split(' ', 2)
        except ValueError:
            writer.close()
            await writer.wait_closed()
            return

        # 2. Read Headers
        content_length = 0
        while True:
            line = await reader.readline()
            if not line or line == b'\r\n' or line == b'\n':
                break
            
            # Look for Content-Length
            line_str = line.decode('utf-8').lower()
            if line_str.startswith("content-length:"):
                try:
                    content_length = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass
        
        # 3. Read Body (if any)
        body = b""
        if content_length > 0:
            body = await reader.readexactly(content_length)
        
        # --- API: Get/Set Message ---
        if path.startswith("/api/message"):
            if method == "POST":
                try:
                    data = ujson.loads(body.decode('utf-8'))
                    # If empty string is sent, it clears the message
                    custom_message = data.get("message", "")
                    print(f"New Message: '{custom_message}'")
                    await send_response(writer, "200 OK", "application/json", '{"status": "ok"}'.encode())
                except Exception as e:
                    print(f"JSON Error: {e}")
                    await send_response(writer, "400 Bad Request", "application/json", '{"error": "invalid json"}'.encode())
            else:
                # GET
                resp = ujson.dumps({"message": custom_message})
                await send_response(writer, "200 OK", "application/json", resp.encode())
            
            writer.close()
            await writer.wait_closed()
            return
            
        # --- API: Settings (LED) ---
        if path.startswith("/api/settings"):
            if method == "POST":
                try:
                    data = ujson.loads(body.decode('utf-8'))
                    
                    if "led" in data:
                        led_manager.toggle(data["led"])
                    
                    if "brightness" in data:
                        led_manager.set_brightness(data["brightness"])
                        
                    if "mode" in data:
                        # 0=Auto, 1=Manual
                        m = int(data["mode"])
                        led_manager.set_mode(m)
                        
                    if "pixel" in data:
                        # {"index": 0, "r": 255, "g": 0, "b": 0}
                        p = data["pixel"]
                        led_manager.set_manual_pixel(p.get("index", 0), p.get("r", 0), p.get("g", 0), p.get("b", 0))

                    await send_response(writer, "200 OK", "application/json", '{"status": "ok"}'.encode())
                except Exception as e:
                    print(f"Settings Error: {e}")
                    await send_response(writer, "400 Bad Request", "application/json", '{"error": "invalid json"}'.encode())
            else:
                resp = ujson.dumps({
                    "led": led_manager.ENABLED,
                    "brightness": led_manager.GLOBAL_BRIGHTNESS,
                    "mode": led_manager.CURRENT_MODE,
                    "colors": led_manager.MANUAL_COLORS
                })
                await send_response(writer, "200 OK", "application/json", resp.encode())
                
            writer.close()
            await writer.wait_closed()
            return

        # --- Static File Serving ---
        if path == "/" or path == "/index.html":
            file_path = "index.html"
        else:
            file_path = path.lstrip("/")
            if ".." in file_path:
                await send_response(writer, "403 Forbidden", "text/plain", b"Forbidden")
                writer.close()
                await writer.wait_closed()
                return

        # Try to serve file
        try:
            os.stat(file_path) 
            
            ctype = "text/plain"
            if file_path.endswith(".html"): ctype = "text/html"
            elif file_path.endswith(".css"): ctype = "text/css"
            elif file_path.endswith(".js"): ctype = "application/javascript"
            elif file_path.endswith(".json"): ctype = "application/json"
            
            header = f"HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\nConnection: close\r\n\r\n"
            await writer.awrite(header.encode())
            
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk: break
                    await writer.awrite(chunk)
                    
        except OSError:
            await send_response(writer, "404 Not Found", "text/plain", b"File Not Found")

    except Exception as e:
        print(f"Web Error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def start_server():
    print("Starting Async Web Server on Port 80...")
    await uasyncio.start_server(handle_client, "0.0.0.0", 80)

