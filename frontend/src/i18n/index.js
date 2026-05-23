import { createI18n } from 'vue-i18n'
import enUS from '../locales/en-US.js'
import zhCN from '../locales/zh-CN.js'

export const LOCALE_STORAGE_KEY = 'saveany-locale'
export const SUPPORTED_LOCALES = ['zh-CN', 'en-US']

const messages = {
  'zh-CN': zhCN,
  'en-US': enUS,
}

function detectLocale() {
  if (typeof window === 'undefined') {
    return 'zh-CN'
  }
  const saved = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  if (saved && SUPPORTED_LOCALES.includes(saved)) {
    return saved
  }
  const lang = (navigator.language || 'zh-CN').toLowerCase()
  return lang.startsWith('zh') ? 'zh-CN' : 'en-US'
}

export function applyDocumentLocale(locale) {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.lang = locale === 'zh-CN' ? 'zh-CN' : 'en'
}

const initialLocale = detectLocale()
applyDocumentLocale(initialLocale)

const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'zh-CN',
  messages,
})

export default i18n
