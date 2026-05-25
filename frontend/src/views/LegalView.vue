<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const { t, tm } = useI18n()

const SUPPORT_EMAIL = 'support@cozyguidehub.com'

const legalKey = computed(() => route.meta.legalKey || 'privacy')

const sections = computed(() => {
  const raw = tm(`legal.${legalKey.value}.sections`)
  return Array.isArray(raw) ? raw : []
})

function legalText(text) {
  if (typeof text !== 'string') return text
  return text.replace(/\{supportEmail\}/g, SUPPORT_EMAIL)
}
</script>

<template>
  <article class="legal-page">
    <header class="legal-header">
      <RouterLink class="back-link" to="/">{{ t('legal.backHome') }}</RouterLink>
      <h1>{{ t(`legal.${legalKey}.title`) }}</h1>
      <p class="legal-updated">{{ t('legal.lastUpdated', { date: t(`legal.${legalKey}.date`) }) }}</p>
    </header>

    <section v-for="(section, index) in sections" :key="index" class="legal-section">
      <h2>{{ section.title }}</h2>
      <p v-for="(para, pIdx) in section.paragraphs" :key="pIdx">{{ legalText(para) }}</p>
      <ul v-if="section.items?.length">
        <li v-for="(item, iIdx) in section.items" :key="iIdx">{{ legalText(item) }}</li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.legal-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 40px 24px 80px;
  color: #1e2430;
  line-height: 1.7;
}
.legal-header {
  margin-bottom: 32px;
}
.back-link {
  display: inline-block;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 600;
  color: #2268f0;
}
.legal-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
}
.legal-updated {
  margin: 0;
  font-size: 13px;
  color: #67758a;
}
.legal-section {
  margin-bottom: 28px;
}
.legal-section h2 {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 700;
}
.legal-section p {
  margin: 0 0 10px;
  font-size: 14.5px;
  color: #3d4654;
}
.legal-section ul {
  margin: 0 0 10px;
  padding-left: 1.25rem;
  font-size: 14.5px;
  color: #3d4654;
}
.legal-section li {
  margin-bottom: 6px;
}
</style>
