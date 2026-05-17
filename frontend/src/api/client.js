const parseError = async (response) => {
  try {
    const data = await response.json()
    return data.detail || data.message || '请求失败，请稍后重试'
  } catch {
    return '请求失败，请稍后重试'
  }
}

export const request = async (url, options = {}) => {
  const response = await fetch(url, {
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
