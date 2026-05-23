<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t, tm } = useI18n()

const toolReasons = computed(() => {
  const raw = tm('help.youtubeCookies.toolReasons')
  return Array.isArray(raw) ? raw : []
})

const securityItems = computed(() => {
  const raw = tm('help.youtubeCookies.securityItems')
  return Array.isArray(raw) ? raw : []
})

const steps = computed(() => {
  const raw = tm('help.youtubeCookies.steps')
  return Array.isArray(raw) ? raw : []
})

const toolStoreUrl = computed(() => t('help.youtubeCookies.toolStoreUrl'))
</script>

<template>
  <article class="help-page">
    <header class="help-header">
      <RouterLink class="back-link" to="/">{{ t('help.youtubeCookies.backHome') }}</RouterLink>
      <h1>{{ t('help.youtubeCookies.title') }}</h1>
    </header>

    <section class="help-section">
      <h2>{{ t('help.youtubeCookies.whyTitle') }}</h2>
      <p>{{ t('help.youtubeCookies.whyBody') }}</p>
    </section>

    <section class="help-section help-tool">
      <h2>{{ t('help.youtubeCookies.toolTitle') }}</h2>
      <p class="help-tool-name">
        <a
          class="help-tool-link"
          :href="toolStoreUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ t('help.youtubeCookies.toolName') }}
        </a>
      </p>
      <ul>
        <li v-for="(reason, index) in toolReasons" :key="index">{{ reason }}</li>
      </ul>
    </section>

    <section class="help-section help-callout">
      <h2>{{ t('help.youtubeCookies.securityTitle') }}</h2>
      <ul>
        <li v-for="(item, index) in securityItems" :key="index">{{ item }}</li>
      </ul>
    </section>

    <section class="help-section">
      <h2>{{ t('help.youtubeCookies.stepsTitle') }}</h2>
      <ol>
        <li v-if="steps[0]">{{ steps[0] }}</li>
        <li>
          {{ t('help.youtubeCookies.step2Before') }}
          <a
            class="help-store-link"
            :href="toolStoreUrl"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ t('help.youtubeCookies.toolName') }}
          </a>
          {{ t('help.youtubeCookies.step2After') }}
        </li>
        <li v-for="(step, index) in steps.slice(1)" :key="index + 1">{{ step }}</li>
      </ol>
    </section>

    <section class="help-section help-warning">
      <h2>{{ t('help.youtubeCookies.warningTitle') }}</h2>
      <p>{{ t('help.youtubeCookies.warningNoPassword') }}</p>
    </section>

    <section class="help-section">
      <h2>{{ t('help.youtubeCookies.successTitle') }}</h2>
      <p>{{ t('help.youtubeCookies.successBody') }}</p>
    </section>

    <p class="help-footer-cta">
      <RouterLink class="help-cta-link" to="/">{{ t('help.youtubeCookies.backToApp') }}</RouterLink>
    </p>
  </article>
</template>

<style scoped>
.help-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 40px 24px 80px;
  color: #1e2430;
  line-height: 1.7;
}

.help-header {
  margin-bottom: 32px;
}

.back-link {
  display: inline-block;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 600;
  color: #2268f0;
  text-decoration: none;
}

.help-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}

.help-section {
  margin-bottom: 28px;
}

.help-section h2 {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 700;
}

.help-section p {
  margin: 0 0 10px;
  font-size: 14.5px;
  color: #3d4654;
}

.help-tool {
  padding: 16px 18px;
  background: #f5f9ff;
  border: 1px solid #dce8ff;
  border-radius: 14px;
}

.help-tool-name {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 800;
}

.help-tool-link,
.help-store-link {
  color: #2268f0;
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.help-tool-link:hover,
.help-store-link:hover {
  color: #1a54c4;
}

.help-tool ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 14.5px;
  color: #3d4654;
}

.help-tool li {
  margin-bottom: 8px;
}

.help-callout {
  padding: 16px 18px;
  background: #fff8f5;
  border: 1px solid #ffe0d6;
  border-radius: 14px;
}

.help-callout ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 14.5px;
  color: #3d4654;
}

.help-callout li {
  margin-bottom: 8px;
}

.help-section ol {
  margin: 0;
  padding-left: 1.35rem;
  font-size: 14.5px;
  color: #3d4654;
}

.help-section ol li {
  margin-bottom: 8px;
}

.help-warning {
  padding: 14px 16px;
  background: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 12px;
}

.help-warning p {
  margin: 0;
  color: #9f1239;
  font-weight: 600;
}

.help-footer-cta {
  margin-top: 36px;
  text-align: center;
}

.help-cta-link {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  padding: 0 20px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
  text-decoration: none;
  background: linear-gradient(135deg, #ff6b35 0%, #e85d2c 100%);
  border-radius: 999px;
}
</style>
