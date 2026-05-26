const MAX_EMAIL_LENGTH = 254
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const BLOCKED_EMAILS = new Set([
  'test@test.com',
  'abc@abc.com',
  'admin@admin.com',
  'demo@demo.com',
  'fake@fake.com',
  '1@1.com',
  'a@a.com',
  'example@example.com',
])

const BLOCKED_DOMAINS = new Set([
  'example.com',
  'example.net',
  'example.org',
  'test.com',
  'invalid.com',
])

export function normalizeEmail(email) {
  return (email || '').trim().toLowerCase()
}

function isPlaceholderEmail(emailNorm) {
  if (BLOCKED_EMAILS.has(emailNorm)) return true
  const at = emailNorm.indexOf('@')
  if (at <= 0 || at === emailNorm.length - 1) return true
  const domain = emailNorm.slice(at + 1)
  return BLOCKED_DOMAINS.has(domain)
}

/**
 * @returns {'required'|'invalid'|'placeholder'|null}
 */
export function getRegisterEmailErrorKey(email) {
  const normalized = normalizeEmail(email)
  if (!normalized) return 'required'
  if (normalized.length > MAX_EMAIL_LENGTH) return 'invalid'
  if (!EMAIL_PATTERN.test(normalized)) return 'invalid'
  if (isPlaceholderEmail(normalized)) return 'placeholder'
  return null
}

export function isRegisterEmailApiError(message) {
  const text = String(message || '')
  if (!text) return false
  return /邮箱|email|Email|有效|placeholder|测试|real email|valid email/i.test(text)
}
