<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t, tm } = useI18n()

const EXTENSION_IMG = '/help/youtube-cookies-extension.png'
const UPLOAD_IMG = '/help/youtube-cookies-upload.png'

const lightboxSrc = ref('')
const lightboxDialog = ref(null)

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

const guideFigures = computed(() => [
  {
    src: EXTENSION_IMG,
    titleKey: 'figure1Title',
    captionKey: 'figure1Caption',
    altKey: 'figure1Alt',
  },
  {
    src: UPLOAD_IMG,
    titleKey: 'figure2Title',
    captionKey: 'figure2Caption',
    altKey: 'figure2Alt',
  },
])

const openLightbox = (src) => {
  lightboxSrc.value = src
  lightboxDialog.value?.showModal()
}

const closeLightbox = () => {
  lightboxDialog.value?.close()
  lightboxSrc.value = ''
}
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

    <section class="help-section help-callout">
      <h2>{{ t('help.youtubeCookies.expectationsTitle') }}</h2>
      <p>{{ t('help.youtubeCookies.expectationsBody') }}</p>
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

    <section class="help-section help-visuals" :aria-label="t('help.youtubeCookies.visualsTitle')">
      <h2>{{ t('help.youtubeCookies.visualsTitle') }}</h2>
      <div class="help-figure-list">
        <figure v-for="(figure, index) in guideFigures" :key="index" class="help-figure">
          <button
            type="button"
            class="help-figure-zoom"
            :aria-label="t(`help.youtubeCookies.${figure.altKey}`)"
            @click="openLightbox(figure.src)"
          >
            <img
              :src="figure.src"
              :alt="t(`help.youtubeCookies.${figure.altKey}`)"
              class="help-figure-image"
              loading="lazy"
              decoding="async"
            />
          </button>
          <figcaption class="help-figure-caption">
            <strong>{{ t(`help.youtubeCookies.${figure.titleKey}`) }}</strong>
            <p>{{ t(`help.youtubeCookies.${figure.captionKey}`) }}</p>
          </figcaption>
        </figure>
      </div>
    </section>

    <dialog ref="lightboxDialog" class="help-lightbox" @click="closeLightbox" @cancel="closeLightbox">
      <button type="button" class="help-lightbox-close" @click="closeLightbox">
        {{ t('help.youtubeCookies.lightboxClose') }}
      </button>
      <img v-if="lightboxSrc" :src="lightboxSrc" class="help-lightbox-image" alt="" @click.stop />
    </dialog>

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

.help-visuals {
  padding: 18px 18px 6px;
  background: #f8fbff;
  border: 1px solid #e8eef7;
  border-radius: 14px;
}

.help-figure-list {
  display: grid;
  gap: 22px;
}

.help-figure {
  margin: 0;
}

.help-figure-zoom {
  display: block;
  width: 100%;
  padding: 0;
  border: 1px solid #dce6f5;
  border-radius: 12px;
  background: #ffffff;
  cursor: zoom-in;
  overflow: hidden;
}

.help-figure-image {
  display: block;
  width: 100%;
  max-height: 320px;
  object-fit: contain;
  object-position: top center;
}

.help-figure-caption {
  margin-top: 10px;
}

.help-figure-caption strong {
  display: block;
  margin-bottom: 6px;
  font-size: 14.5px;
  color: #1a2540;
}

.help-figure-caption p {
  margin: 0;
  font-size: 13.5px;
  color: #6b7791;
  line-height: 1.55;
}

.help-lightbox {
  width: min(96vw, 960px);
  max-width: 96vw;
  max-height: 92vh;
  padding: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
}

.help-lightbox::backdrop {
  background: rgba(15, 23, 42, 0.72);
}

.help-lightbox-image {
  display: block;
  width: 100%;
  max-height: 86vh;
  object-fit: contain;
  border-radius: 12px;
  background: #ffffff;
}

.help-lightbox-close {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2;
  min-height: 36px;
  padding: 0 14px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  cursor: pointer;
}

.help-footer-cta {
  margin-top: 36px;
  text-align: center;
}

@media (max-width: 560px) {
  .help-figure-image {
    max-height: 240px;
  }
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
