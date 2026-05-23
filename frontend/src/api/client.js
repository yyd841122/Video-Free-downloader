// 生产构建（vite build）默认指向线上后端域名；
// 本地 `npm run dev` 保持空字符串，由 Vite dev server 的 /api 代理转发到本地后端。
// 如需在构建期临时覆盖（例如预发环境），可以设置 VITE_API_BASE_URL=https://...
const DEFAULT_PROD_API_BASE_URL = 'https://api-videodown.cozyguidehub.com'
const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const API_BASE_URL =
  RAW_API_BASE_URL || (import.meta.env.PROD ? DEFAULT_PROD_API_BASE_URL : '')

const resolveApiUrl = (url) => {
  if (!url) return url
  if (/^https?:\/\//i.test(url)) return url
  if (!API_BASE_URL) return url
  return url.startsWith('/') ? `${API_BASE_URL}${url}` : `${API_BASE_URL}/${url}`
}

const parseError = async (response) => {
  try {
    const data = await response.json()
    return data.detail || data.message || '请求失败，请稍后重试'
  } catch {
    return '请求失败，请稍后重试'
  }
}

export const request = async (url, options = {}) => {
  const response = await fetch(resolveApiUrl(url), {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

export const requestForm = async (url, formData) => {
  const response = await fetch(resolveApiUrl(url), {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseError(response))
  }

  return response.json()
}

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
