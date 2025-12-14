<script setup>
import { ref } from 'vue'

const password = ref('')
const error = ref('')
const loading = ref(false)

const emit = defineEmits(['login'])

const login = async () => {
  if (!password.value) return
  loading.value = true
  error.value = ''
  
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value })
    })
    
    const data = await res.json()
    if (res.ok) {
      localStorage.setItem('token', data.token)
      emit('login', data.token)
    } else {
      error.value = data.error || 'Login failed'
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
    <h2>🔐 Login</h2>
    <form @submit.prevent="login">
      <input type="password" v-model="password" placeholder="Enter Password" autofocus>
      <div v-if="error" class="error">{{ error }}</div>
      <button class="primary full-width" :disabled="loading">
        {{ loading ? 'Checking...' : 'Login' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-card { max-width: 350px; margin: 60px auto; text-align: center; padding: 2rem; border-radius: 12px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
h2 { margin-bottom: 1.5rem; color: #333; }
input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #e1e4e8; border-radius: 8px; font-size: 16px; box-sizing: border-box; transition: border-color 0.2s; }
input:focus { border-color: #007bff; outline: none; }
button { width: 100%; padding: 12px; font-size: 16px; margin-top: 10px; }
.error { color: #dc3545; margin-bottom: 15px; font-size: 0.9rem; background: #fff5f5; padding: 8px; border-radius: 6px; }
</style>
