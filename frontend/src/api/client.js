// 生产构建（vite build）默认指向线上后端域名；
// 本地 `npm run dev` 保持空字符串，由 Vite dev server 的 /api 代理转发到本地后端。
// 如需在构建期临时覆盖（例如预发环境），可以设置 VITE_API_BASE_URL=https://...
const DEFAULT_PROD_API_BASE_URL = 'https://api-videodown.cozyguidehub.com'
const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const API_BASE_URL =
  RAW_API_BASE_URL || (import.meta.env.PROD ? DEFAULT_PROD_API_BASE_URL : '')

export const resolveApiUrl = (url) => {
  if (!url) return url
  if (/^https?:\/\//i.test(url)) return url
  if (!API_BASE_URL) return url
  return url.startsWith('/') ? `${API_BASE_URL}${url}` : `${API_BASE_URL}/${url}`
}

const TOKEN_STORAGE_KEY = 'saveany:auth-token'

export const getAuthToken = () => {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export const setAuthToken = (token) => {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    /* ignore */
  }
}

const unauthorizedHandlers = new Set()

export const onUnauthorized = (handler) => {
  unauthorizedHandlers.add(handler)
  return () => unauthorizedHandlers.delete(handler)
}

const fireUnauthorized = () => {
  for (const handler of unauthorizedHandlers) {
    try {
      handler()
    } catch {
      /* ignore */
    }
  }
}

const parseError = async (response) => {
  if (response.status === 404) {
    return '接口不存在（Not Found）。请重启后端到最新版本后再试。'
  }
  try {
    const data = await response.json()
    const detail = data.detail || data.message
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
    }
    return '请求失败，请稍后重试'
  } catch {
    return '请求失败，请稍后重试'
  }
}

const withAuthHeaders = (extra = {}) => {
  const token = getAuthToken()
  if (!token) return extra
  return { Authorization: `Bearer ${token}`, ...extra }
}

export const request = async (url, options = {}) => {
  const response = await fetch(resolveApiUrl(url), {
    headers: withAuthHeaders({
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }),
    ...options,
  })

  if (response.status === 401) {
    setAuthToken('')
    fireUnauthorized()
    throw new Error(await parseError(response))
  }

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

export const requestForm = async (url, formData) => {
  const response = await fetch(resolveApiUrl(url), {
    method: 'POST',
    headers: withAuthHeaders(),
    body: formData,
  })

  if (response.status === 401) {
    setAuthToken('')
    fireUnauthorized()
    throw new Error(await parseError(response))
  }
  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

// ===================== 视频下载 / AI 总结（已有） =====================
export const getVideoInfo = (url, cookies = '', browserCookies = '', authSessionId = '') =>
  request('/api/video/info', {
    method: 'POST',
    body: JSON.stringify({
      url,
      cookies: cookies || null,
      browser_cookies: browserCookies || null,
      auth_session_id: authSessionId || null,
    }),
  })

export const createDownloadTask = (payload) =>
  request('/api/video/download', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getTask = (taskId) => request(`/api/tasks/${taskId}`)

export const createDirectLink = (payload) =>
  request('/api/video/direct', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const createBiliQrCode = () =>
  request('/api/auth/bilibili/qrcode', {
    method: 'POST',
  })

export const getBiliQrStatus = (sessionId) => request(`/api/auth/bilibili/qrcode/${sessionId}`)

export const createAiSummaryTask = (payload) =>
  request('/api/ai/summary', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const getAiSummaryTask = (taskId) => request(`/api/ai/summary/${taskId}`)

export const chatWithAiSummary = (taskId, payload) =>
  request(`/api/ai/summary/${taskId}/chat`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const createAiSummaryFromSubtitle = ({ file, title = '', url = '' }) => {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }
  if (url) {
    formData.append('url', url)
  }
  return requestForm('/api/ai/summary/subtitle', formData)
}

// ===================== 用户与会员 =====================
export const registerUser = (payload) =>
  request('/api/users/register', { method: 'POST', body: JSON.stringify(payload) })

export const loginUser = (payload) =>
  request('/api/users/login', { method: 'POST', body: JSON.stringify(payload) })

export const fetchCurrentUser = () => request('/api/users/me')

export const fetchQuota = () => request('/api/users/me/quota')

export const fetchTaskHistory = () => request('/api/users/me/history')

export const createBatchDownload = (payload) =>
  request('/api/video/batch', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

// ===================== 支付 / 套餐 =====================
export const fetchPlans = () => request('/api/billing/plans')

export const fetchBillingMode = () => request('/api/billing/mode')

export const createCheckout = (planCode) =>
  request('/api/billing/checkout', { method: 'POST', body: JSON.stringify({ plan_code: planCode }) })

export const fetchOrders = () => request('/api/billing/orders')

export const fetchOrder = (orderNo) => request(`/api/billing/orders/${orderNo}`)

export const mockPay = (orderNo, outcome) =>
  request(`/api/billing/mock/pay/${orderNo}`, {
    method: 'POST',
    body: JSON.stringify({ outcome }),
  })
