<script setup>
import { useI18n } from 'vue-i18n'
import { applyDocumentLocale, LOCALE_STORAGE_KEY, SUPPORTED_LOCALES } from '../i18n'

const { locale, t } = useI18n()

const setLocale = (value) => {
  if (!SUPPORTED_LOCALES.includes(value) || locale.value === value) {
    return
  }
  locale.value = value
  window.localStorage.setItem(LOCALE_STORAGE_KEY, value)
  applyDocumentLocale(value)
}
</script>

<template>
  <div class="lang-switcher" role="group" :aria-label="t('nav.langLabel')">
    <button
      type="button"
      class="lang-option"
      :class="{ active: locale === 'zh-CN' }"
      :aria-pressed="locale === 'zh-CN'"
      @click="setLocale('zh-CN')"
    >
      {{ t('nav.langZh') }}
    </button>
    <button
      type="button"
      class="lang-option"
      :class="{ active: locale === 'en-US' }"
      :aria-pressed="locale === 'en-US'"
      @click="setLocale('en-US')"
    >
      {{ t('nav.langEn') }}
    </button>
  </div>
</template>

<style scoped>
.lang-switcher {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(34, 104, 240, 0.12);
  border-radius: 999px;
  gap: 2px;
}

.lang-option {
  min-width: 44px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #5f6b7c;
  background: transparent;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.lang-option:hover {
  color: #2268f0;
  background: rgba(34, 104, 240, 0.06);
}

.lang-option.active {
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  box-shadow: 0 6px 14px rgba(45, 116, 241, 0.22);
}
</style>
