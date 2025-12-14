from microdot import Microdot, send_file
import ujson
import os
import wifi_manager
import led_manager
import machine
import time

app = Microdot()

# --- API Endpoints ---

@app.route('/api/message', methods=['GET', 'POST'])
async def api_message(request):
    global custom_message
    if request.method == 'POST':
        print(f"Message POST: {request.json}") # Debug
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
        print(f"Settings POST: {request.json}") # Debug
        try:
            data = request.json
            if data is None: 
                return {'error': 'no json'}, 400
                
            if "led" in data:
                print(f"Toggle LED: {data['led']}")
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
            print(f"Settings Error: {e}")
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

@app.route('/api/scan')
async def api_scan(request):
    try:
        networks = wifi_manager.scan_networks()
        return ujson.dumps(networks), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/wifi', methods=['POST'])
async def api_wifi(request):
    try:
        data = request.json
        ssid = data.get("ssid")
        pw = data.get("password")
        if ssid:
            wifi_manager.save_config(ssid, pw)
            # Schedule reboot
            # We can't reboot immediately or the response won't send.
            # Microdot doesn't have background tasks built-in easily without asyncio loop access.
            # But we are in async handler.
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

# --- Static File Serving ---

@app.route('/')
async def index(request):
    # Serve different apps based on mode? Or just one Unified App?
    # Let's serve the main app.
    return send_file('www/index.html')

@app.route('/setup')
async def setup_page(request):
    # In AP mode, redirect here? Or just handle in frontend router?
    return send_file('www/index.html') 

@app.route('/assets/<path:path>')
async def static_assets(request, path):
    # Serve JS/CSS from www/assets/
    return send_file('www/assets/' + path)

@app.route('/<path:path>')
async def static_root(request, path):
    # Fallback for other files like favicon.ico
    return send_file('www/' + path)

# Global State
custom_message = ""

async def start_server():
    print("Starting Microdot Server...")
    await app.start_server(host='0.0.0.0', port=80, debug=True)