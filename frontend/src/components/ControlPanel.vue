<script setup>
import { ref, reactive, nextTick, defineProps } from 'vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'

const props = defineProps(['state'])
const emit = defineEmits(['update:state', 'refresh'])

const newMessage = ref('')
const sending = ref(false)
const contentMode = ref('text')

// Cropper
const showCropper = ref(false)
const imageSrc = ref('')
let cropper = null
const imageRef = ref(null)

const authFetch = async (url, options = {}) => {
  const token = localStorage.getItem('token')
  const headers = { ...options.headers }
  if (token) headers['X-Token'] = token
  
  const res = await fetch(url, { ...options, headers })
  if (res.status === 401) {
    location.reload()
    throw new Error('Unauthorized')
  }
  return res
}

const updateMessage = async () => {
  sending.value = true
  try {
    await authFetch('/api/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: newMessage.value })
    })
    emit('refresh')
    newMessage.value = ''
  } catch (e) {
    alert("Failed")
  } finally {
    sending.value = false
  }
}

const clearMessage = async () => {
  newMessage.value = ''
  await updateMessage()
}

// Settings Helpers
const updateSettings = async (body) => {
  await authFetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  emit('refresh')
}

const toggleLed = () => updateSettings({ led: !props.state.led })

const rgbToHex = (rgb) => "#" + ((1 << 24) + (rgb[0] << 16) + (rgb[1] << 8) + rgb[2]).toString(16).slice(1)
const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)] : null;
}

const updatePixel = (idx, hex) => {
  const rgb = hexToRgb(hex)
  if (!rgb) return
  // Optimistic update local state if needed, but fetch usually handles it
  updateSettings({ pixel: { index: idx, r: rgb[0], g: rgb[1], b: rgb[2] } })
}

// Image Logic
const onFileSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  imageSrc.value = URL.createObjectURL(file)
  showCropper.value = true
  
  nextTick(() => {
    if (cropper) cropper.destroy()
    cropper = new Cropper(imageRef.value, {
      aspectRatio: 128 / 296,
      viewMode: 1,
      autoCropArea: 1,
    })
  })
  event.target.value = ''
}

const cancelCrop = () => {
  showCropper.value = false
  if (cropper) cropper.destroy()
}

const uploadCropped = async () => {
  if (!cropper) return
  sending.value = true
  
  const canvas = cropper.getCroppedCanvas({
    width: 128, height: 296, imageSmoothingQuality: 'high'
  })
  
  const ctx = canvas.getContext('2d')
  const imageData = ctx.getImageData(0, 0, 128, 296)
  const data = imageData.data
  const width = 128
  const height = 296
  
  // Dithering
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const oldPixel = (data[idx] + data[idx+1] + data[idx+2]) / 3
      const newPixel = oldPixel < 128 ? 0 : 255
      const quantError = oldPixel - newPixel
      
      data[idx] = data[idx+1] = data[idx+2] = newPixel
      
      const diffuse = (x, y, factor) => {
          if (x >= 0 && x < width && y < height) {
              const i = (y * width + x) * 4
              const v = (data[i] + data[i+1] + data[i+2]) / 3 + quantError * factor
              data[i] = data[i+1] = data[i+2] = v
          }
      }
      diffuse(x + 1, y, 7/16)
      diffuse(x - 1, y + 1, 3/16)
      diffuse(x, y + 1, 5/16)
      diffuse(x + 1, y + 1, 1/16)
    }
  }
  
  // Pack
  const buffer = new Uint8Array(width * height / 8)
  for (let i = 0; i < width * height; i++) {
      const pixelIdx = i * 4
      const val = data[pixelIdx] > 128 ? 1 : 0
      const byteIdx = Math.floor(i / 8)
      const bitIdx = 7 - (i % 8)
      if (val) buffer[byteIdx] |= (1 << bitIdx)
  }
  
  try {
      await authFetch('/api/display/image', { method: 'POST', body: buffer })
      emit('refresh')
      showCropper.value = false
  } catch (e) {
      alert("Upload failed")
  } finally {
      sending.value = false
  }
}
</script>

<template>
  <div class="card content-card">
    <h2>Display Content</h2>
    
    <div class="sub-tabs">
      <span :class="{active: contentMode==='text'}" @click="contentMode='text'">Text</span>
      <span :class="{active: contentMode==='image'}" @click="contentMode='image'">Image</span>
    </div>

    <!-- Text Mode -->
    <div v-if="contentMode === 'text'" class="content-body">
      <div class="message-preview">{{ props.state.message === '__IMAGE__' ? '[Image Displayed]' : (props.state.message || 'Empty') }}</div>
      <div class="input-group">
        <input v-model="newMessage" placeholder="Type message..." @keyup.enter="updateMessage">
        <button @click="updateMessage" :disabled="sending">Send</button>
      </div>
      <button class="secondary full-width" @click="clearMessage">Clear Screen</button>
    </div>

    <!-- Image Mode -->
    <div v-if="contentMode === 'image'" class="content-body">
      <div class="upload-area" v-if="!showCropper">
        <label class="file-label">
          <input type="file" accept="image/*" @change="onFileSelect" :disabled="sending">
          <span>{{ sending ? 'Processing...' : 'Choose Image' }}</span>
        </label>
      </div>
      
      <!-- Cropper UI -->
      <div v-show="showCropper" class="cropper-ui">
        <div class="crop-container">
          <img ref="imageRef" :src="imageSrc" style="max-width: 100%;">
        </div>
        <div class="crop-actions">
          <button class="secondary" @click="cancelCrop">Cancel</button>
          <button class="primary" @click="uploadCropped" :disabled="sending">{{ sending ? 'Uploading...' : 'Upload' }}</button>
        </div>
      </div>
      
      <p class="hint" v-if="!showCropper">Images are automatically dithered.</p>
    </div>
  </div>

  <div class="card">
    <div class="row header-row">
      <h2>LED Control</h2>
      <label class="switch">
        <input type="checkbox" :checked="props.state.led" @change="toggleLed">
        <span class="slider"></span>
      </label>
    </div>

    <div v-if="props.state.led" class="led-settings">
      <div class="control-row">
        <label>Brightness</label>
        <input type="range" :value="props.state.brightness" min="0" max="1" step="0.05" @change="updateSettings({brightness: parseFloat($event.target.value)})">
      </div>
      
      <div class="control-row">
        <label>Mode</label>
        <select :value="props.state.mode" @change="updateSettings({mode: parseInt($event.target.value)})">
          <option :value="0">Auto (Status)</option>
          <option :value="1">Manual</option>
        </select>
      </div>

      <div v-if="props.state.mode === 1" class="pixels">
        <div v-for="(color, idx) in props.state.colors" :key="idx" class="pixel-control">
          <input type="color" :value="rgbToHex(color)" @input="updatePixel(idx, $event.target.value)">
          <span>{{ idx+1 }}</span>
        </div>
      </div>
    </div>
  </div>
  
  <div class="footer">
    Storage: {{ (props.state.storage?.free / 1024).toFixed(1) }} KB Free
  </div>
</template>

<style scoped>
/* Content Area */
.message-preview { background: #f1f3f5; padding: 20px; border-radius: 8px; font-size: 1.2rem; font-weight: bold; text-align: center; margin-bottom: 20px; border: 1px dashed #ced4da; color: #495057; min-height: 40px; display: flex; align-items: center; justify-content: center; word-break: break-word; }

/* Upload Area */
.upload-area { border: 2px dashed #e1e4e8; border-radius: 12px; padding: 40px 20px; text-align: center; transition: all 0.2s; background: #fafafa; cursor: pointer; }
.upload-area:hover { border-color: #007bff; background: #f0f7ff; }
.file-label { display: inline-block; width: 100%; height: 100%; cursor: pointer; }
.file-label input { display: none; }
.file-label span { background: #007bff; color: white; padding: 10px 24px; border-radius: 6px; font-weight: 500; display: inline-block; transition: background 0.2s; }
.file-label span:hover { background: #0056b3; }
.hint { text-align: center; font-size: 0.85rem; color: #888; margin-top: 15px; }

/* Cropper */
.cropper-ui { text-align: center; background: #f8f9fa; padding: 15px; border-radius: 8px; }
.crop-container { height: 300px; margin-bottom: 15px; background: #333; border-radius: 4px; overflow: hidden; }
.crop-actions { display: flex; gap: 10px; justify-content: center; }

/* LED Section */
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
.control-row { margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between; }
.control-row label { font-weight: 500; font-size: 0.95rem; color: #555; }
.control-row input[type="range"], .control-row select { width: 60%; margin: 0; }

/* Pixels */
.pixels { display: flex; justify-content: center; gap: 15px; margin-top: 25px; background: #f8f9fa; padding: 15px; border-radius: 8px; }
.pixel-control { display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 0.8rem; color: #666; }
input[type="color"] { width: 45px; height: 45px; border: 2px solid #ddd; border-radius: 50%; padding: 0; overflow: hidden; cursor: pointer; transition: transform 0.1s; }
input[type="color"]:hover { transform: scale(1.1); border-color: #aaa; }

/* Toggle Switch */
.switch { position: relative; display: inline-block; width: 48px; height: 26px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #e9ecef; transition: .3s; border-radius: 34px; border: 1px solid #ced4da; }
.slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 2px; bottom: 2px; background-color: white; transition: .3s; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
input:checked + .slider { background-color: #28a745; border-color: #28a745; }
input:checked + .slider:before { transform: translateX(22px); }

.footer { text-align: center; color: #adb5bd; font-size: 0.8rem; margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px; }
</style>
