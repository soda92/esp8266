<script setup>
import { ref, onMounted, reactive } from 'vue'

const currentMessage = ref('')
const newMessage = ref('')
const ledEnabled = ref(true)
const brightness = ref(0.1)
const ledMode = ref(0)
const ledColors = ref([[0,0,0], [0,0,0], [0,0,0], [0,0,0]])
const storage = reactive({ free: 0, total: 0 })
const loading = ref(true)
const sending = ref(false)
const wifiNetworks = ref([])
const scanning = ref(false)
const wifiForm = reactive({ ssid: '', password: '' })

// Mode: 'control' or 'setup'
const uiMode = ref('control')
// Content Tab: 'text' or 'image'
const contentMode = ref('text')

const fetchData = async () => {
  try {
    const [msgRes, ledRes] = await Promise.all([
      fetch('/api/message'),
      fetch('/api/settings')
    ])
    
    const msgData = await msgRes.json()
    const ledData = await ledRes.json()
    
    currentMessage.value = msgData.message
    ledEnabled.value = ledData.led
    brightness.value = ledData.brightness
    ledMode.value = ledData.mode
    ledColors.value = ledData.colors || [[0,0,0],[0,0,0],[0,0,0],[0,0,0]]
    storage.free = ledData.storage_free || 0
    storage.total = ledData.storage_total || 0
    
    loading.value = false
  } catch (e) {
    console.error("Fetch error", e)
  }
}

const updateMessage = async () => {
  sending.value = true
  try {
    await fetch('/api/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: newMessage.value })
    })
    currentMessage.value = newMessage.value
    newMessage.value = ''
  } catch (e) {
    alert("Failed")
  } finally {
    sending.value = false
  }
}

const processImage = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  sending.value = true // Reuse sending state
  
  const img = new Image()
  img.src = URL.createObjectURL(file)
  
  img.onload = async () => {
    const width = 128
    const height = 296
    
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    
    // Fill white first
    ctx.fillStyle = 'white'
    ctx.fillRect(0, 0, width, height)
    
    // Draw image (cover/contain)
    const scale = Math.max(width / img.width, height / img.height)
    const x = (width / 2) - (img.width / 2) * scale
    const y = (height / 2) - (img.height / 2) * scale
    ctx.drawImage(img, x, y, img.width * scale, img.height * scale)
    
    const imageData = ctx.getImageData(0, 0, width, height)
    const data = imageData.data
    
    // Floyd-Steinberg Dithering
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4
        const oldPixel = (data[idx] + data[idx+1] + data[idx+2]) / 3
        const newPixel = oldPixel < 128 ? 0 : 255
        const quantError = oldPixel - newPixel
        
        data[idx] = data[idx+1] = data[idx+2] = newPixel
        
        if (x + 1 < width) {
          const i = (y * width + x + 1) * 4
          const v = (data[i] + data[i+1] + data[i+2]) / 3 + quantError * 7 / 16
          data[i] = data[i+1] = data[i+2] = v
        }
        if (x - 1 >= 0 && y + 1 < height) {
          const i = ((y + 1) * width + x - 1) * 4
          const v = (data[i] + data[i+1] + data[i+2]) / 3 + quantError * 3 / 16
          data[i] = data[i+1] = data[i+2] = v
        }
        if (y + 1 < height) {
          const i = ((y + 1) * width + x) * 4
          const v = (data[i] + data[i+1] + data[i+2]) / 3 + quantError * 5 / 16
          data[i] = data[i+1] = data[i+2] = v
        }
        if (x + 1 < width && y + 1 < height) {
          const i = ((y + 1) * width + x + 1) * 4
          const v = (data[i] + data[i+1] + data[i+2]) / 3 + quantError * 1 / 16
          data[i] = data[i+1] = data[i+2] = v
        }
      }
    }
    
    // Pack bits (MONO_HLSB: 1=White, 0=Black)
    const buffer = new Uint8Array(width * height / 8)
    for (let i = 0; i < width * height; i++) {
        const pixelIdx = i * 4
        const val = data[pixelIdx] > 128 ? 1 : 0
        const byteIdx = Math.floor(i / 8)
        const bitIdx = 7 - (i % 8)
        if (val) buffer[byteIdx] |= (1 << bitIdx)
    }
    
    try {
        await fetch('/api/display/image', {
            method: 'POST',
            body: buffer
        })
        currentMessage.value = "__IMAGE__"
    } catch (e) {
        alert("Upload failed")
    } finally {
        sending.value = false
        event.target.value = '' // Reset input
    }
  }
}

const clearMessage = async () => {
  newMessage.value = ''
  await updateMessage()
}

const toggleLed = async () => {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ led: ledEnabled.value })
  })
}

const updateSettings = async (body) => {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
}

const rgbToHex = (rgb) => "#" + ((1 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]).toString(16).slice(1)
const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)] : null;
}

const updatePixel = (idx, hex) => {
  const rgb = hexToRgb(hex)
  if (!rgb) return
  ledColors.value[idx] = rgb
  updateSettings({ pixel: { index: idx, r: rgb[0], g: rgb[1], b: rgb[2] } })
}

const scanWifi = async () => {
  scanning.value = true
  try {
    const res = await fetch('/api/scan')
    wifiNetworks.value = await res.json()
  } catch(e) {
    alert("Scan failed")
  } finally {
    scanning.value = false
  }
}

const saveWifi = async () => {
  if(!wifiForm.ssid) return
  try {
    await fetch('/api/wifi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(wifiForm)
    })
    alert("Saved! Rebooting...")
  } catch(e) {
    alert("Error saving")
  }
}

onMounted(() => {
  if (window.location.hostname === '192.168.4.1') {
    uiMode.value = 'setup'
  }
  fetchData()
  setInterval(fetchData, 5000)
})
</script>

<template>
  <div class="container">
    <header>
      <h1>📡 ESP32 Hub</h1>
      <div class="main-tabs">
        <button :class="{active: uiMode==='control'}" @click="uiMode='control'">Control</button>
        <button :class="{active: uiMode==='setup'}" @click="uiMode='setup'">WiFi Setup</button>
      </div>
    </header>

    <main v-if="uiMode === 'control'">
      <div class="card content-card">
        <h2>Display Content</h2>
        
        <div class="sub-tabs">
          <span :class="{active: contentMode==='text'}" @click="contentMode='text'">Text</span>
          <span :class="{active: contentMode==='image'}" @click="contentMode='image'">Image</span>
        </div>

        <div v-if="contentMode === 'text'" class="content-body">
          <div class="message-preview">{{ currentMessage === '__IMAGE__' ? '[Image Displayed]' : (currentMessage || 'Empty') }}</div>
          <div class="input-group">
            <input v-model="newMessage" placeholder="Type message..." @keyup.enter="updateMessage">
            <button @click="updateMessage" :disabled="sending">Send</button>
          </div>
          <button class="secondary full-width" @click="clearMessage">Clear Screen</button>
        </div>

        <div v-if="contentMode === 'image'" class="content-body">
          <div class="upload-area">
            <label class="file-label">
              <input type="file" accept="image/*" @change="processImage" :disabled="sending">
              <span>{{ sending ? 'Processing...' : 'Choose Image' }}</span>
            </label>
          </div>
          <p class="hint">Images are automatically dithered to 1-bit.</p>
        </div>
      </div>

      <div class="card">
        <div class="row header-row">
          <h2>LED Control</h2>
          <label class="switch">
            <input type="checkbox" v-model="ledEnabled" @change="toggleLed">
            <span class="slider"></span>
          </label>
        </div>

        <div v-if="ledEnabled" class="led-settings">
          <div class="control-row">
            <label>Brightness</label>
            <input type="range" v-model.number="brightness" min="0" max="1" step="0.05" @change="updateSettings({brightness})">
          </div>
          
          <div class="control-row">
            <label>Mode</label>
            <select v-model.number="ledMode" @change="updateSettings({mode: ledMode})">
              <option :value="0">Auto (Status)</option>
              <option :value="1">Manual</option>
            </select>
          </div>

          <div v-if="ledMode === 1" class="pixels">
            <div v-for="(color, idx) in ledColors" :key="idx" class="pixel-control">
              <input type="color" :value="rgbToHex(color)" @input="updatePixel(idx, $event.target.value)">
              <span>{{ idx+1 }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="footer">
        Storage: {{ (storage.free / 1024).toFixed(1) }} KB Free
      </div>
    </main>

    <main v-else>
      <div class="card">
        <h2>WiFi Settings</h2>
        <button class="full-width" @click="scanWifi" :disabled="scanning">{{ scanning ? 'Scanning...' : 'Scan Networks' }}</button>
        
        <ul class="wifi-list" v-if="wifiNetworks.length">
          <li v-for="net in wifiNetworks" @click="wifiForm.ssid = net.ssid">
            <span class="ssid">{{ net.ssid }}</span>
            <span class="rssi">{{ net.rssi }}dBm</span>
          </li>
        </ul>

        <div class="form">
          <input v-model="wifiForm.ssid" placeholder="SSID">
          <input v-model="wifiForm.password" type="password" placeholder="Password">
          <button class="primary full-width" @click="saveWifi">Save & Connect</button>
        </div>
      </div>
    </main>
  </div>
</template>

<style>
:root { --primary: #007bff; --bg: #f4f6f8; --card-bg: #ffffff; --text: #2c3e50; --border: #e1e4e8; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: var(--text); }
.container { max-width: 480px; margin: 0 auto; }
.card { background: var(--card-bg); padding: 20px; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
h1 { font-size: 1.5rem; margin: 0; color: #1a1a1a; }
h2 { font-size: 1.1rem; margin: 0 0 15px 0; font-weight: 600; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }

/* Buttons & Inputs */
input[type="text"], input[type="password"], select { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 16px; background: #f9f9f9; box-sizing: border-box; margin-bottom: 10px; }
input:focus { outline: 2px solid var(--primary); border-color: transparent; }
button { padding: 10px 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s; background: #e2e6ea; color: var(--text); }
button.active { background: var(--primary); color: white; }
button.primary { background: var(--primary); color: white; }
button.secondary { background: #f1f3f5; color: #495057; }
button.full-width { width: 100%; margin-top: 10px; }
button:disabled { opacity: 0.6; cursor: not-allowed; }

/* Tabs */
.main-tabs { display: flex; gap: 8px; background: white; padding: 4px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
.sub-tabs { display: flex; margin-bottom: 15px; border-bottom: 1px solid var(--border); }
.sub-tabs span { padding: 10px 20px; cursor: pointer; font-weight: 500; color: #888; position: relative; }
.sub-tabs span.active { color: var(--primary); }
.sub-tabs span.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: var(--primary); }

/* Content */
.message-preview { background: #f8f9fa; padding: 15px; border-radius: 8px; font-size: 1.2rem; font-weight: bold; text-align: center; margin-bottom: 15px; border: 1px dashed var(--border); color: #555; }
.input-group { display: flex; gap: 8px; }
.input-group input { margin: 0; }

/* Upload */
.upload-area { border: 2px dashed var(--border); border-radius: 12px; padding: 30px; text-align: center; transition: border-color 0.2s; }
.upload-area:hover { border-color: var(--primary); }
.file-label { cursor: pointer; display: inline-block; }
.file-label input { display: none; }
.file-label span { background: var(--primary); color: white; padding: 10px 20px; border-radius: 8px; font-weight: 500; }
.hint { text-align: center; font-size: 0.8rem; color: #888; margin-top: 10px; }

/* LED Controls */
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
.control-row { margin-bottom: 15px; }
.control-row label { display: block; margin-bottom: 5px; font-weight: 500; font-size: 0.9rem; }
.pixels { display: flex; justify-content: space-between; gap: 10px; margin-top: 20px; }
.pixel-control { display: flex; flex-direction: column; align-items: center; gap: 5px; font-size: 0.8rem; color: #666; }
input[type="color"] { width: 40px; height: 40px; border: none; border-radius: 50%; padding: 0; overflow: hidden; cursor: pointer; }

/* WiFi List */
.wifi-list { list-style: none; padding: 0; margin: 15px 0; border: 1px solid var(--border); border-radius: 8px; max-height: 250px; overflow-y: auto; }
.wifi-list li { padding: 12px; border-bottom: 1px solid var(--border); cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
.wifi-list li:hover { background: #f8f9fa; }
.wifi-list li:last-child { border-bottom: none; }
.ssid { font-weight: 500; }
.rssi { font-size: 0.8rem; color: #888; background: #eee; padding: 2px 6px; border-radius: 4px; }

/* Toggle */
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 34px; }
.slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
input:checked + .slider { background-color: var(--primary); }
input:checked + .slider:before { transform: translateX(20px); }

.footer { text-align: center; color: #999; font-size: 0.8rem; margin-top: 30px; }
</style>
