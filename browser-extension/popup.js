const API_BASE = 'http://127.0.0.1:8000/api'

const elements = {
  statusBadge: document.querySelector('#statusBadge'),
  pageTitle: document.querySelector('#pageTitle'),
  pageUrl: document.querySelector('#pageUrl'),
  sensitiveToggle: document.querySelector('#sensitiveToggle'),
  startButton: document.querySelector('#startButton'),
  stopButton: document.querySelector('#stopButton'),
  countText: document.querySelector('#countText'),
  requestList: document.querySelector('#requestList'),
  sendButton: document.querySelector('#sendButton'),
  copyButton: document.querySelector('#copyButton'),
  clearButton: document.querySelector('#clearButton'),
  messageText: document.querySelector('#messageText'),
}

let activeTab = null
let currentState = null

const sendRuntimeMessage = (message) =>
  new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message))
        return
      }
      if (!response?.ok) {
        reject(new Error(response?.error || '插件通信失败'))
        return
      }
      resolve(response.data)
    })
  })

const getActiveTab = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab
}

const buildPayload = () => ({
  page_url: currentState?.pageUrl || activeTab?.url || '',
  page_title: currentState?.pageTitle || activeTab?.title || '',
  include_sensitive_headers: Boolean(currentState?.includeSensitiveHeaders),
  media_requests: currentState?.mediaRequests || [],
})

const render = () => {
  const enabled = Boolean(currentState?.enabled)
  const requests = currentState?.mediaRequests || []

  elements.statusBadge.textContent = enabled ? '捕获中' : '未开启'
  elements.statusBadge.classList.toggle('is-active', enabled)
  elements.pageTitle.textContent = currentState?.pageTitle || activeTab?.title || '当前页面'
  elements.pageUrl.textContent = currentState?.pageUrl || activeTab?.url || ''
  elements.sensitiveToggle.checked = Boolean(currentState?.includeSensitiveHeaders)
  elements.countText.textContent = `${requests.length} 条`
  elements.stopButton.disabled = !enabled
  elements.sendButton.disabled = requests.length === 0
  elements.copyButton.disabled = requests.length === 0

  elements.requestList.innerHTML = ''
  if (!requests.length) {
    const empty = document.createElement('p')
    empty.className = 'hint'
    empty.textContent = '开启捕获后，在当前视频页播放视频，这里会出现 m3u8、mp4、m4s 等媒体请求。'
    elements.requestList.append(empty)
    return
  }

  requests.slice(0, 20).forEach((request) => {
    const item = document.createElement('article')
    item.className = 'request-item'

    const type = document.createElement('p')
    type.className = 'request-type'
    type.textContent = request.type || request.method || 'media'

    const url = document.createElement('p')
    url.className = 'request-url'
    url.textContent = request.url

    item.append(type, url)
    elements.requestList.append(item)
  })
}

const refreshState = async () => {
  activeTab = await getActiveTab()
  currentState = await sendRuntimeMessage({ type: 'GET_STATE', tabId: activeTab.id })
  render()
}

const showMessage = (message, isError = false) => {
  elements.messageText.textContent = message
  elements.messageText.style.color = isError ? '#c01048' : '#057647'
}

elements.startButton.addEventListener('click', async () => {
  currentState = await sendRuntimeMessage({
    type: 'START_CAPTURE',
    tabId: activeTab.id,
    pageUrl: activeTab.url,
    pageTitle: activeTab.title,
    includeSensitiveHeaders: elements.sensitiveToggle.checked,
  })
  showMessage('已开始捕获。请在视频页点击播放。')
  render()
})

elements.stopButton.addEventListener('click', async () => {
  currentState = await sendRuntimeMessage({ type: 'STOP_CAPTURE', tabId: activeTab.id })
  showMessage('已停止捕获。')
  render()
})

elements.clearButton.addEventListener('click', async () => {
  currentState = await sendRuntimeMessage({ type: 'CLEAR_CAPTURE', tabId: activeTab.id })
  showMessage('捕获结果已清空。')
  render()
})

elements.copyButton.addEventListener('click', async () => {
  await navigator.clipboard.writeText(JSON.stringify(buildPayload(), null, 2))
  showMessage('已复制 JSON。')
})

elements.sendButton.addEventListener('click', async () => {
  try {
    const response = await fetch(`${API_BASE}/extension/captures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildPayload()),
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '发送失败')
    }
    showMessage(`已发送到本地服务：${data.capture_id}`)
  } catch (error) {
    showMessage(error.message, true)
  }
})

refreshState().catch((error) => showMessage(error.message, true))
setInterval(() => {
  if (activeTab?.id) {
    refreshState().catch(() => {})
  }
}, 1200)
