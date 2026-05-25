const URL_IN_TEXT_RE = /https?:\/\/[^\s<>"'[\](){}]+/i
const TRAILING_PUNCT_RE = /[,，。.;；!?！？)、】』」\]\/]+$/u

function stripTrailingPunctuation(value) {
  let s = String(value || '').trim()
  while (s && TRAILING_PUNCT_RE.test(s)) {
    s = s.replace(TRAILING_PUNCT_RE, '')
  }
  return s
}

function extractFirstUrl(text) {
  const match = String(text || '').match(URL_IN_TEXT_RE)
  if (!match) {
    return null
  }
  return stripTrailingPunctuation(match[0])
}

function parseUrlSafe(url) {
  try {
    return new URL(url)
  } catch {
    return null
  }
}

function isBilibiliHost(hostname) {
  const host = String(hostname || '').toLowerCase()
  return /(^|\.)bilibili\.com$/i.test(host) || /(^|\.)b23\.tv$/i.test(host)
}

function isDouyinHost(hostname) {
  const host = String(hostname || '').toLowerCase()
  return /(^|\.)douyin\.com$/i.test(host)
}

function isXHost(hostname) {
  const host = String(hostname || '').toLowerCase()
  return /(^|\.)twitter\.com$/i.test(host) || /(^|\.)x\.com$/i.test(host)
}

function isMp4Url(urlString, pathname, search) {
  const combined = `${pathname || ''}${search || ''}`
  return /\.mp4(\?|#|$)/i.test(combined) || /\.mp4/i.test(urlString)
}

function isXStatusPath(pathname) {
  return /\/status\/\d+/i.test(pathname || '')
}

function normalizeBilibiliUrl(parsed) {
  const path = (parsed.pathname || '').replace(/\/+$/, '') || ''
  parsed.search = ''
  parsed.hash = ''
  if (/^\/video\/BV[\w-]+$/i.test(path)) {
    parsed.pathname = `${path}/`
  }
  return parsed.toString()
}

function normalizeDouyinModalId(parsed) {
  const modalId = parsed.searchParams.get('modal_id')
  if (modalId && /^\d+$/.test(modalId)) {
    return `https://www.iesdouyin.com/share/video/${modalId}/`
  }
  return null
}

function normalizeDouyinUrl(parsed) {
  const modalNormalized = normalizeDouyinModalId(parsed)
  if (modalNormalized) {
    return modalNormalized
  }

  const path = parsed.pathname || '/'
  if (/^\/video\/\d+$/.test(path)) {
    parsed.search = ''
    parsed.hash = ''
    return parsed.toString()
  }

  parsed.search = ''
  parsed.hash = ''
  parsed.pathname = path.endsWith('/') ? path : `${path}/`
  return parsed.toString()
}

function normalizeXUrl(parsed) {
  parsed.search = ''
  parsed.hash = ''
  return parsed.toString()
}

/**
 * @param {string} raw
 * @returns {{ url: string, changed: boolean, error?: string }}
 */
export function normalizeUserVideoInput(raw) {
  const trimmed = String(raw ?? '').trim()
  if (!trimmed) {
    return { url: '', changed: false, error: 'empty' }
  }

  let candidate = extractFirstUrl(trimmed)
  if (!candidate && /^https?:\/\//i.test(trimmed)) {
    candidate = stripTrailingPunctuation(trimmed)
  }
  if (!candidate) {
    return { url: '', changed: false, error: 'no_url' }
  }

  const parsed = parseUrlSafe(candidate)
  if (!parsed) {
    return { url: '', changed: false, error: 'invalid_url' }
  }

  const host = parsed.hostname
  let normalized = candidate

  if (isMp4Url(candidate, parsed.pathname, parsed.search)) {
    normalized = candidate
  } else if (isBilibiliHost(host)) {
    normalized = normalizeBilibiliUrl(parsed)
  } else if (isDouyinHost(host)) {
    normalized = normalizeDouyinUrl(parsed)
  } else if (isXHost(host) && isXStatusPath(parsed.pathname)) {
    normalized = normalizeXUrl(parsed)
  } else {
    normalized = candidate
  }

  return {
    url: normalized,
    changed: normalized !== trimmed,
    error: undefined,
  }
}
