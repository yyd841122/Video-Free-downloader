const MAX_RECORDS_PER_TAB = 200
const SAFE_HEADER_NAMES = new Set([
  'accept',
  'accept-language',
  'origin',
  'range',
  'referer',
  'user-agent',
])
const SENSITIVE_HEADER_NAMES = new Set(['authorization', 'cookie'])
const MEDIA_URL_PATTERN = /\.(m3u8|mpd|m4s|ts|mp4|webm|flv|mov)(\?|#|$)/i
const MEDIA_RESOURCE_TYPES = new Set(['media', 'xmlhttprequest', 'other'])

const stateKey = (tabId) => `capture:${tabId}`

const getTabState = async (tabId) => {
  const result = await chrome.storage.local.get(stateKey(tabId))
  return result[stateKey(tabId)] || {
    enabled: false,
    includeSensitiveHeaders: false,
    pageUrl: '',
    pageTitle: '',
    mediaRequests: [],
  }
}

const setTabState = async (tabId, state) => {
  await chrome.storage.local.set({ [stateKey(tabId)]: state })
}

const normalizeHeaders = (headers = [], includeSensitiveHeaders = false) => {
  return headers
    .filter((header) => {
      const name = String(header.name || '').toLowerCase()
      return SAFE_HEADER_NAMES.has(name) || (includeSensitiveHeaders && SENSITIVE_HEADER_NAMES.has(name))
    })
    .map((header) => ({ name: header.name, value: header.value || '' }))
}

const isLikelyMediaRequest = (details) => {
  if (MEDIA_URL_PATTERN.test(details.url)) {
    return true
  }
  return MEDIA_RESOURCE_TYPES.has(details.type)
}

const storeMediaRequest = async (details) => {
  if (details.tabId < 0 || !isLikelyMediaRequest(details)) {
    return
  }

  const tabState = await getTabState(details.tabId)
  if (!tabState.enabled) {
    return
  }

  const mediaRequests = tabState.mediaRequests || []
  const existingIndex = mediaRequests.findIndex((item) => item.url === details.url)
  const record = {
    url: details.url,
    method: details.method || 'GET',
    type: details.type || 'other',
    request_headers: normalizeHeaders(details.requestHeaders, tabState.includeSensitiveHeaders),
    timestamp: Date.now(),
  }

  if (existingIndex >= 0) {
    mediaRequests[existingIndex] = record
  } else {
    mediaRequests.unshift(record)
  }

  tabState.mediaRequests = mediaRequests.slice(0, MAX_RECORDS_PER_TAB)
  await setTabState(details.tabId, tabState)
}

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    storeMediaRequest(details)
  },
  { urls: ['<all_urls>'] },
  ['requestHeaders', 'extraHeaders'],
)

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.remove(stateKey(tabId))
})

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handle = async () => {
    if (message.type === 'GET_STATE') {
      return getTabState(message.tabId)
    }

    if (message.type === 'START_CAPTURE') {
      const previous = await getTabState(message.tabId)
      const next = {
        ...previous,
        enabled: true,
        includeSensitiveHeaders: Boolean(message.includeSensitiveHeaders),
        pageUrl: message.pageUrl || previous.pageUrl,
        pageTitle: message.pageTitle || previous.pageTitle,
        mediaRequests: [],
      }
      await setTabState(message.tabId, next)
      return next
    }

    if (message.type === 'STOP_CAPTURE') {
      const previous = await getTabState(message.tabId)
      const next = { ...previous, enabled: false }
      await setTabState(message.tabId, next)
      return next
    }

    if (message.type === 'CLEAR_CAPTURE') {
      const previous = await getTabState(message.tabId)
      const next = { ...previous, mediaRequests: [] }
      await setTabState(message.tabId, next)
      return next
    }

    throw new Error(`Unknown message type: ${message.type}`)
  }

  handle()
    .then((result) => sendResponse({ ok: true, data: result }))
    .catch((error) => sendResponse({ ok: false, error: error.message }))
  return true
})
