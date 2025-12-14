from microdot import Microdot, send_file, Request
import ujson
import os
import wifi_manager
import led_manager
import machine
import auth_manager
import ubinascii
import logger
import time

# Increase Body Limit for OTA
Request.max_content_length = 1024 * 1024
Request.max_body_length = 1024 * 1024

app = Microdot()

sessions = set()

def get_token(request):
    return request.headers.get("X-Token")

@app.before_request
async def check_auth(request):
    path = request.path
    # Public paths
    if path.startswith("/assets") or path == "/" or path == "/index.html" or path == "/setup":
        return
    if path.startswith("/api/auth"):
        return
    
    # Check Token
    token = get_token(request)
    if not token or token not in sessions:
        return {'error': 'unauthorized'}, 401

@app.route('/api/logs', methods=['GET', 'DELETE'])
async def api_logs(request):
    if request.method == 'DELETE':
        logger.clear()
        return {'status': 'cleared'}
    else:
        return {'logs': logger.get_logs()}

@app.route('/api/auth/status')
async def auth_status(request):
    try:
        return {'setup': auth_manager.is_setup()}
    except Exception as e:
        print(f"Auth Status Error: {e}")
        return {'error': str(e)}, 500

@app.route('/api/auth/setup', methods=['POST'])
async def auth_setup(request):
    if auth_manager.is_setup():
        return {'error': 'already setup'}, 403
    
    data = request.json
    password = data.get("password")
    if not password: return {'error': 'missing password'}, 400
    
    auth_manager.set_password(password)
    return {'status': 'ok'}

@app.route('/api/auth/login', methods=['POST'])
async def auth_login(request):
    data = request.json
    password = data.get("password")
    if auth_manager.verify_password(password):
        # Generate simple token (random hex)
        token = ubinascii.hexlify(os.urandom(16)).decode()
        sessions.add(token)
        return {'token': token}
    else:
        return {'error': 'invalid password'}, 401

@app.route('/api/auth/reset', methods=['POST'])
async def auth_reset(request):
    data = request.json
    serial = data.get("serial")
    if auth_manager.factory_reset(serial):
        return {'status': 'reset'}
    else:
        return {'error': 'invalid serial'}, 403

# --- Key Management ---

@app.route('/api/ota/key', methods=['POST'])
async def api_ota_key(request):
    try:
        key_data = request.body
        if len(key_data) != 32:
            if len(key_data) == 64:
                try: key_data = ubinascii.unhexlify(key_data)
                except: pass
        
        # Ensure keys dir exists
        try: os.mkdir('/keys')
        except: pass
        
        # Generate filename using time to be unique
        fname = f"/keys/user_{time.time()}.key"
        
        with open(fname, "w") as f:
            f.write(key_data.hex()) 
            
        return {'status': 'key added', 'file': fname}
    except Exception as e:
        return {'error': str(e)}, 500

# --- Existing API ---

@app.route('/api/message', methods=['GET', 'POST'])
async def api_message(request):
    global custom_message
    if request.method == 'POST':
        try:
            data = request.json
            if data is None:
                return {'error': 'no json received'}, 400
                
            custom_message = data.get("message", "")
            print(f"Set Message to: '{custom_message}'")
            return {'status': 'ok'}
        except Exception as e:
            print(f"Msg Error: {e}")
            return {'error': str(e)}, 400
    else:
        return {'message': custom_message}

@app.route('/api/settings', methods=['GET', 'POST'])
async def api_settings(request):
    if request.method == 'POST':
        try:
            data = request.json
            if data is None: 
                return {'error': 'no json'}, 400
                
            if "led" in data:
                led_manager.toggle(data["led"])
            if "brightness" in data:
                led_manager.set_brightness(data["brightness"])
            if "mode" in data:
                led_manager.set_mode(int(data["mode"]))
            if "pixel" in data:
                p = data["pixel"]
                led_manager.set_manual_pixel(p.get("index", 0), p.get("r", 0), p.get("g", 0), p.get("b", 0))
            return {'status': 'ok'}
        except Exception as e:
            return {'error': str(e)}, 400
    else:
        s = os.statvfs('/')
        return {
            "led": led_manager.ENABLED,
            "brightness": led_manager.GLOBAL_BRIGHTNESS,
            "mode": led_manager.CURRENT_MODE,
            "colors": led_manager.MANUAL_COLORS,
            "storage_free": s[0] * s[3],
            "storage_total": s[0] * s[2]
        }

@app.route('/api/display/image', methods=['POST'])
async def api_display_image(request):
    global custom_message
    try:
        data = request.body
        if len(data) != 4736:
            return {'error': f'Invalid size: {len(data)}, expected 4736'}, 400
            
        with open('image.bin', 'wb') as f:
            f.write(data)
            
        custom_message = "__IMAGE__"
        print("Image Received and Saved")
        return {'status': 'ok'}
        
    except Exception as e:
        print(f"Image Upload Error: {e}")
        return {'error': str(e)}, 500

@app.route('/api/wifi', methods=['POST'])
async def api_wifi(request):
    try:
        data = request.json
        ssid = data.get("ssid")
        pw = data.get("password")
        if ssid:
            wifi_manager.save_config(ssid, pw)
            import uasyncio
            async def reboot_later():
                await uasyncio.sleep(1)
                machine.reset()
            uasyncio.create_task(reboot_later())
            return {'status': 'saved', 'action': 'rebooting'}
        else:
            return {'error': 'missing ssid'}, 400
    except Exception as e:
        return {'error': str(e)}, 400

@app.route('/api/ota', methods=['POST'])
async def api_ota(request):
    import ota_manager
    import ubinascii
    
    try:
        sig_hex = request.headers.get('X-Signature')
        if not sig_hex:
            return {'error': 'missing signature'}, 400
            
        signature = ubinascii.unhexlify(sig_hex)
        zip_data = request.body
        
        if ota_manager.verify_and_install(zip_data, signature):
            return {'status': 'updating'}
        else:
            return {'error': 'invalid signature'}, 403
            
    except Exception as e:
        print(f"OTA Error: {e}")
        return {'error': str(e)}, 500

@app.route('/api/scan')
async def api_scan(request):
    try:
        networks = wifi_manager.scan_networks()
        return ujson.dumps(networks), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return {'error': str(e)}, 500

# --- Static File Serving ---

@app.route('/')
async def index(request):
    return send_file('www/index.html')

@app.route('/setup')
async def setup_page(request):
    return send_file('www/index.html') 

@app.route('/assets/<path:path>')
async def static_assets(request, path):
    return send_file('www/assets/' + path)

@app.route('/<path:path>')
async def static_root(request, path):
    # Fallback logic
    if path in ["generate_204", "hotspot-detect.html", "canonical.html", "ncsi.txt"]:
        # Captive Portal Probes
        # Redirect to root
        return '', 302, {'Location': '/'}
        
    try:
        # Try to serve file
        return send_file('www/' + path)
    except:
        # If 404, just serve index? Or let it 404?
        # For SPA (Vue Router), we usually serve index.html.
        # Let's serve index.html if file missing
        return send_file('www/index.html')

# Global State
custom_message = ""

async def start_server():
    print("Starting Microdot Server...")
    await app.start_server(host='0.0.0.0', port=80, debug=True)
