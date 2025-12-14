<script setup>
import { ref } from 'vue'

const password = ref('')
const confirm = ref('')
const error = ref('')
const loading = ref(false)

const emit = defineEmits(['setup-complete'])

const setup = async () => {
  if (password.value !== confirm.value) {
    error.value = "Passwords don't match"
    return
  }
  
  loading.value = true
  try {
    const res = await fetch('/api/auth/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value })
    })
    
    if (res.ok) {
      alert("Password set! Please login.")
      emit('setup-complete')
    } else {
      error.value = 'Setup failed'
    }
  } catch (e) {
    error.value = 'Connection error'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card login-card">
    <h2>🆕 First Time Setup</h2>
    <p>Set a password for your device.</p>
    <form @submit.prevent="setup">
      <input type="password" v-model="password" placeholder="New Password" required>
      <input type="password" v-model="confirm" placeholder="Confirm Password" required>
      <div v-if="error" class="error">{{ error }}</div>
      <button class="primary full-width" :disabled="loading">
        {{ loading ? 'Saving...' : 'Set Password' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-card { max-width: 350px; margin: 60px auto; text-align: center; padding: 2rem; border-radius: 12px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
h2 { margin-bottom: 10px; color: #333; }
p { color: #666; margin-bottom: 20px; font-size: 0.95rem; }
input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #e1e4e8; border-radius: 8px; font-size: 16px; box-sizing: border-box; transition: border-color 0.2s; }
input:focus { border-color: #007bff; outline: none; }
button { width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }
.error { color: #dc3545; margin-bottom: 15px; font-size: 0.9rem; background: #fff5f5; padding: 8px; border-radius: 6px; }
</style>
