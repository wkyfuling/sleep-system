import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')

  const isLoggedIn = computed(() => !!accessToken.value && !!user.value)
  const role = computed(() => user.value?.role || null)

  function _setSession({ user: u, access, refresh }) {
    user.value = u
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('user', JSON.stringify(u))
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  async function login(payload) {
    const data = await authApi.login(payload)
    _setSession(data)
    return data
  }

  async function register(payload) {
    const data = await authApi.register(payload)
    _setSession(data)
    return data
  }

  async function fetchMe() {
    const { user: u } = await authApi.me()
    user.value = u
    localStorage.setItem('user', JSON.stringify(u))
    return u
  }

  function logout() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('user')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function setAccessToken(token) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
  }

  return {
    user, accessToken, refreshToken,
    isLoggedIn, role,
    login, register, fetchMe, logout, setAccessToken,
  }
})
