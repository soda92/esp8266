<script setup>
import { ref, reactive } from 'vue'

const wifiNetworks = ref([])
const scanning = ref(false)
const wifiForm = reactive({ ssid: '', password: '' })
const uploadingKey = ref(false)
const serialInput = ref('')
const resetting = ref(false)

const authFetch = async (url, options = {}) => {
  const token = localStorage.getItem('token')
  const headers = { ...options.headers }
  if (token) headers['X-Token'] = token
  
  const res = await fetch(url, { ...options, headers })
  if (res.status === 401) {
    location.reload() // Force re-login
    throw new Error('Unauthorized')
  }
  return res
}

const scanWifi = async () => {
  scanning.value = true
  try {
    const res = await authFetch('/api/scan')
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
    await authFetch('/api/wifi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(wifiForm)
    })
    alert("Saved! Rebooting...")
  } catch(e) {
    alert("Error saving")
  }
}

const uploadKey = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  uploadingKey.value = true
  try {
    const buffer = await file.arrayBuffer()
    const res = await authFetch('/api/ota/key', {
      method: 'POST',
      body: buffer
    })
    if (res.ok) alert("Key Updated!")
    else alert("Failed to update key")
  } catch (e) {
    alert("Upload error")
  } finally {
    uploadingKey.value = false
    event.target.value = ''
  }
}

const factoryReset = async () => {
  if (!confirm("Are you sure? This will wipe settings.")) return
  
  resetting.value = true
  try {
    const res = await authFetch('/api/auth/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ serial: serialInput.value })
    })
    
    if (res.ok) {
      alert("Reset Successful! Device rebooting...")
      localStorage.removeItem('token')
      location.reload()
    } else {
      const data = await res.json()
      alert("Reset Failed: " + (data.error || "Unknown"))
    }
  } catch (e) {
    alert("Error")
  } finally {
    resetting.value = false
  }
}
</script>

<template>
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

  <div class="card">
    <h2>🔐 OTA Security</h2>
    <p class="hint">Upload a new <code>secret.key</code> to enable custom firmware updates.</p>
    <div class="upload-area">
      <label class="file-label">
        <input type="file" @change="uploadKey" :disabled="uploadingKey">
        <span>{{ uploadingKey ? 'Uploading...' : 'Upload Key File' }}</span>
      </label>
    </div>
  </div>
  
  <div class="card danger-zone">
    <h2>⚠️ Factory Reset</h2>
    <p class="hint">Enter Serial Number (Found on device/console) to reset password.</p>
    <input v-model="serialInput" placeholder="Serial Number (e.g. SN-XXXX)" class="serial-input">
    <button class="danger full-width" @click="factoryReset" :disabled="resetting">
        {{ resetting ? 'Resetting...' : 'Factory Reset' }}
    </button>
  </div>
</template>

<style scoped>
.wifi-list { list-style: none; padding: 0; margin: 15px 0; border: 1px solid #e1e4e8; border-radius: 8px; max-height: 200px; overflow-y: auto; background: #f9f9f9; }
.wifi-list li { padding: 12px 15px; border-bottom: 1px solid #e1e4e8; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s; }
.wifi-list li:hover { background: #eef2f5; }
.wifi-list li:last-child { border-bottom: none; }
.ssid { font-weight: 500; color: #333; }
.rssi { font-size: 0.75rem; color: #666; background: #dfe1e5; padding: 2px 6px; border-radius: 4px; }

.form input { margin-bottom: 10px; width: 100%; box-sizing: border-box; }

.upload-area { border: 2px dashed #e1e4e8; border-radius: 12px; padding: 25px; text-align: center; transition: border-color 0.2s; background: #fafafa; }
.upload-area:hover { border-color: #007bff; background: #f0f7ff; }
.file-label { display: inline-block; cursor: pointer; }
.file-label input { display: none; }
.file-label span { background: #6c757d; color: white; padding: 10px 20px; border-radius: 6px; font-size: 0.9rem; transition: background 0.2s; }
.file-label span:hover { background: #5a6268; }

.hint { font-size: 0.85rem; color: #666; margin-bottom: 15px; line-height: 1.4; }

.danger-zone { border: 1px solid #ffcccc; background: #fffbfb; margin-top: 20px; }
.danger-zone h2 { color: #d93025; font-size: 1.1rem; }
.serial-input { border-color: #ffcccc; background: white; }
.serial-input:focus { border-color: #d93025; }
button.danger { background: #d93025; color: white; margin-top: 10px; }
button.danger:hover { background: #c52b1e; }
</style>
