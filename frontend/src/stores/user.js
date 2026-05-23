import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  fetchCurrentUser,
  getAuthToken,
  loginUser,
  onUnauthorized,
  registerUser,
  setAuthToken,
} from '../api/client'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const initialized = ref(false)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isVip = computed(() => !!user.value?.is_vip)
  const vipLabel = computed(() => {
    if (!user.value) return ''
    if (user.value.is_lifetime_vip) return '终身会员'
    if (!user.value.is_vip) return ''
    if (user.value.vip_expire_at) {
      const date = new Date(user.value.vip_expire_at * 1000)
      const yyyy = date.getFullYear()
      const mm = String(date.getMonth() + 1).padStart(2, '0')
      const dd = String(date.getDate()).padStart(2, '0')
      return `会员有效期至 ${yyyy}-${mm}-${dd}`
    }
    return '会员'
  })

  const setUser = (payload) => {
    user.value = payload || null
  }

  const refresh = async () => {
    if (!getAuthToken()) {
      user.value = null
      initialized.value = true
      return null
    }
    try {
      const data = await fetchCurrentUser()
      user.value = data
      return data
    } catch {
      user.value = null
      setAuthToken('')
      return null
    } finally {
      initialized.value = true
    }
  }

  const login = async (email, password) => {
    loading.value = true
    try {
      const data = await loginUser({ email, password })
      setAuthToken(data.access_token)
      user.value = data.user
      initialized.value = true
      return data.user
    } finally {
      loading.value = false
    }
  }

  const register = async (email, password, nickname) => {
    loading.value = true
    try {
      const data = await registerUser({ email, password, nickname: nickname || null })
      setAuthToken(data.access_token)
      user.value = data.user
      initialized.value = true
      return data.user
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    setAuthToken('')
    user.value = null
  }

  onUnauthorized(() => {
    user.value = null
  })

  return {
    user,
    initialized,
    loading,
    isLoggedIn,
    isVip,
    vipLabel,
    setUser,
    refresh,
    login,
    register,
    logout,
  }
})
