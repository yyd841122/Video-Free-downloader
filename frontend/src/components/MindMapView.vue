<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true,
  },
})

const MAX_MAIN_BRANCHES = 7
const MAX_CHILDREN_PER_BRANCH = 4
const mindmapSvg = ref(null)
const downloadButtonRef = ref(null)
const exportDownloadOpen = ref(false)
const isFullscreen = ref(false)
let markmapInstance = null
let markmapModulesPromise = null

const loadMarkmapModules = () => {
  if (!markmapModulesPromise) {
    markmapModulesPromise = Promise.all([import('markmap-lib'), import('markmap-view')]).then(([lib, view]) => ({
      Transformer: lib.Transformer,
      Markmap: view.Markmap,
    }))
  }
  return markmapModulesPromise
}

const cleanText = (value) =>
  String(value || '')
    .replace(/^\s*\d+[.、)\-]\s*/, '')
    .replace(/\s+/g, ' ')
    .trim()

const containsCjk = (value) => /[\u3400-\u9fff]/u.test(String(value || ''))

const isEnglishSummary = computed(() => {
  const text = [
    props.summary.title,
    props.summary.one_sentence,
    ...(props.summary.outline || []),
    ...(props.summary.key_points || []),
    ...(props.summary.keywords || []),
    props.summary.audience,
  ].join(' ')
  return /[A-Za-z]/.test(text) && !containsCjk(text)
})

const labels = computed(() =>
  isEnglishSummary.value
    ? {
        title: 'Mind Map',
        fit: 'Fit',
        fullscreen: 'Fullscreen',
        exitFullscreen: 'Exit Fullscreen',
        download: 'Download',
        downloadPng: 'HD PNG',
        downloadSvg: 'SVG',
        overview: 'Overview',
        coreTopic: 'Core Topic',
        audience: 'Audience',
        outline: 'Content Structure',
        keyPoints: 'Key Takeaways',
        timeline: 'Timeline',
        keywords: 'Keywords',
        suggestions: 'Learning Suggestions',
        root: 'Video Summary',
      }
    : {
        title: '思维导图',
        fit: '适配',
        fullscreen: '全屏',
        exitFullscreen: '退出全屏',
        download: '下载',
        downloadPng: '高清 PNG',
        downloadSvg: 'SVG',
        overview: '视频概述',
        coreTopic: '核心主题',
        audience: '适合人群',
        outline: '内容结构',
        keyPoints: '关键结论',
        timeline: '时间轴',
        keywords: '关键词',
        suggestions: '学习建议',
        root: '视频总结',
      },
)

const getSafeFilename = (name, fallback = 'mind-map') => {
  const cleaned = String(name || fallback)
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 48)
  return cleaned || fallback
}

const normalizeHeadingLine = (line) => cleanText(line).replace(/^#{1,6}\s*/, '')

const hasValidHeadingMarkdown = (value) =>
  String(value || '')
    .split(/\r?\n/)
    .some((line) => /^#{1,6}\s+\S/.test(line.trim()))

const splitSummaryPoint = (value) => {
  const text = cleanText(value)
  const match = text.match(/^([^：:]{2,72})[：:]\s*(.+)$/)
  if (!match) return { title: text, details: [] }
  return {
    title: cleanText(match[1]),
    details: cleanText(match[2])
      .split(/[;；。]\s*|[.!?]\s+/)
      .map(cleanText)
      .filter(Boolean)
      .slice(0, MAX_CHILDREN_PER_BRANCH),
  }
}

const fallbackMindmapMarkdown = computed(() => {
  const lines = [`# ${cleanText(props.summary.title || labels.value.root)}`]

  if (props.summary.one_sentence) {
    lines.push(`## ${labels.value.overview}`)
    lines.push(`### ${labels.value.coreTopic}`)
    lines.push(`#### ${cleanText(props.summary.one_sentence)}`)
  }

  if (props.summary.outline?.length) {
    lines.push(`## ${labels.value.outline}`)
    props.summary.outline.slice(0, MAX_MAIN_BRANCHES).forEach((item) => {
      const point = splitSummaryPoint(item)
      if (!point.title) return
      lines.push(`### ${point.title}`)
      point.details.forEach((detail) => lines.push(`#### ${detail}`))
    })
  }

  if (props.summary.key_points?.length) {
    lines.push(`## ${labels.value.keyPoints}`)
    props.summary.key_points.slice(0, MAX_MAIN_BRANCHES).forEach((item) => {
      const point = splitSummaryPoint(item)
      if (!point.title) return
      lines.push(`### ${point.title}`)
      point.details.forEach((detail) => lines.push(`#### ${detail}`))
    })
  }

  if (props.summary.timeline?.length) {
    lines.push(`## ${labels.value.timeline}`)
    props.summary.timeline.slice(0, 6).forEach((item) => {
      const title = cleanText(`${item.time || ''} ${item.title || ''}`)
      if (!title) return
      lines.push(`### ${title}`)
      if (item.summary) lines.push(`#### ${cleanText(item.summary)}`)
    })
  }

  if (props.summary.keywords?.length) {
    lines.push(`## ${labels.value.keywords}`)
    props.summary.keywords.slice(0, 10).forEach((item) => lines.push(`### ${cleanText(item)}`))
  }

  if (props.summary.learning_suggestions?.length) {
    lines.push(`## ${labels.value.suggestions}`)
    props.summary.learning_suggestions.slice(0, 5).forEach((item) => lines.push(`### ${cleanText(item)}`))
  }

  if (props.summary.audience) {
    lines.push(`## ${labels.value.audience}`)
    lines.push(`### ${cleanText(props.summary.audience)}`)
  }

  return lines.join('\n')
})

const mindmapMarkdown = computed(() => {
  const generated = String(props.summary.mindmap_markdown || '').trim()
  if (!hasValidHeadingMarkdown(generated)) {
    return fallbackMindmapMarkdown.value
  }
  const lines = generated
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^#{1,6}\s+\S/.test(line))
    .map((line) => {
      const level = Math.min(4, (line.match(/^#+/)?.[0].length || 1))
      return `${'#'.repeat(level)} ${normalizeHeadingLine(line)}`
    })
  return lines.join('\n')
})

const renderMindmap = async () => {
  await nextTick()
  if (!mindmapSvg.value || !mindmapMarkdown.value) return
  mindmapSvg.value.innerHTML = ''
  const { Transformer, Markmap } = await loadMarkmapModules()
  const transformer = new Transformer()
  const { root } = transformer.transform(mindmapMarkdown.value)
  markmapInstance = Markmap.create(
    mindmapSvg.value,
    {
      autoFit: true,
      duration: 360,
      maxWidth: 360,
      spacingHorizontal: 92,
      spacingVertical: 12,
      colorFreezeLevel: 2,
      paddingX: 12,
    },
    root,
  )
}

watch(mindmapMarkdown, renderMindmap, { immediate: true })

const fitMindmap = () => {
  markmapInstance?.fit?.()
}

const toggleFullscreen = async () => {
  isFullscreen.value = !isFullscreen.value
  await nextTick()
  fitMindmap()
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

const getExportFilename = (extension) => `${getSafeFilename(props.summary.title || labels.value.root)}-mindmap.${extension}`

const buildExportableSvg = () => {
  if (!mindmapSvg.value) return
  const cloned = mindmapSvg.value.cloneNode(true)
  cloned.querySelectorAll('[transform]').forEach((element) => {
    const transform = element.getAttribute('transform')
    if (transform?.includes('NaN')) {
      element.setAttribute('transform', 'translate(0,0) scale(1)')
    }
  })
  cloned.querySelectorAll('foreignObject').forEach((foreignObject) => {
    const textContent = foreignObject.textContent?.trim() || ''
    if (!textContent) {
      foreignObject.remove()
      return
    }
    const x = Number.parseFloat(foreignObject.getAttribute('x') || '0') || 0
    const y = Number.parseFloat(foreignObject.getAttribute('y') || '0') || 0
    const h = Number.parseFloat(foreignObject.getAttribute('height') || '20') || 20
    const textElement = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    textElement.setAttribute('x', String(x + 4))
    textElement.setAttribute('y', String(y + h / 2 + 5))
    textElement.setAttribute('font-size', '14')
    textElement.setAttribute('font-family', 'Inter, Arial, sans-serif')
    textElement.setAttribute('fill', '#333333')
    textElement.setAttribute('dominant-baseline', 'middle')
    textElement.textContent = textContent
    foreignObject.parentNode?.replaceChild(textElement, foreignObject)
  })
  return cloned
}

const serializeSvg = (svgElement) => {
  const serializer = new XMLSerializer()
  let svgString = serializer.serializeToString(svgElement)
  if (!svgString.includes('xmlns=')) {
    svgString = svgString.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
  }
  return svgString
}

const getContentBBox = () => {
  const svgElement = mindmapSvg.value
  if (!svgElement) return { x: 0, y: 0, width: 1200, height: 800 }
  const rootGroup = svgElement.querySelector('g')
  if (rootGroup) {
    try {
      const bbox = rootGroup.getBBox()
      if (bbox.width > 0 && bbox.height > 0) {
        const transform = rootGroup.getAttribute('transform') || ''
        const translateMatch = transform.match(/translate\(\s*([-\d.e]+)\s*[,\s]\s*([-\d.e]+)\s*\)/)
        const scaleMatch = transform.match(/scale\(\s*([-\d.e]+)/)
        const tx = translateMatch ? Number.parseFloat(translateMatch[1]) : 0
        const ty = translateMatch ? Number.parseFloat(translateMatch[2]) : 0
        const scale = scaleMatch ? Number.parseFloat(scaleMatch[1]) : 1
        return {
          x: bbox.x * scale + tx,
          y: bbox.y * scale + ty,
          width: bbox.width * scale,
          height: bbox.height * scale,
        }
      }
    } catch {
      // Fallback below.
    }
  }
  try {
    const bbox = svgElement.getBBox()
    if (bbox.width > 0 && bbox.height > 0) return bbox
  } catch {
    // Fallback below.
  }
  return { x: 0, y: 0, width: 1200, height: 800 }
}

const setFullViewBox = (svgClone) => {
  const dims = getContentBBox()
  const padding = 60
  const vx = dims.x - padding
  const vy = dims.y - padding
  const vw = Math.max(360, dims.width + padding * 2)
  const vh = Math.max(260, dims.height + padding * 2)
  svgClone.setAttribute('viewBox', `${vx} ${vy} ${vw} ${vh}`)
  svgClone.setAttribute('width', String(vw))
  svgClone.setAttribute('height', String(vh))
  svgClone.setAttribute('style', 'background:#ffffff')
  return { vw, vh }
}

const downloadSvg = () => {
  const cloned = buildExportableSvg()
  if (!cloned) return
  cloned.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  setFullViewBox(cloned)
  const source = serializeSvg(cloned)
  downloadBlob(new Blob([source], { type: 'image/svg+xml;charset=utf-8' }), getExportFilename('svg'))
}

const downloadPng = async () => {
  const cloned = buildExportableSvg()
  if (!cloned) return
  cloned.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const { vw, vh } = setFullViewBox(cloned)
  const source = serializeSvg(cloned)
  const svgBlob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  const image = new Image()
  const scale = Math.max(3, Math.ceil(3840 / vw))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(vw * scale)
  canvas.height = Math.round(vh * scale)
  const context = canvas.getContext('2d')
  return new Promise((resolve) => {
    image.onload = () => {
      context.fillStyle = '#ffffff'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      canvas.toBlob((blob) => {
        if (blob) downloadBlob(blob, getExportFilename('png'))
        resolve()
      }, 'image/png')
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      window.alert('PNG 导出失败，请使用 SVG 下载')
      resolve()
    }
    image.src = url
  })
}

const downloadMindMap = (format) => {
  exportDownloadOpen.value = false
  if (format === 'svg') {
    downloadSvg()
    return
  }
  downloadPng()
}

const toggleExportDownload = () => {
  exportDownloadOpen.value = !exportDownloadOpen.value
}

const downloadMenuStyle = computed(() => {
  const rect = downloadButtonRef.value?.getBoundingClientRect?.()
  if (!rect) return {}
  return {
    top: `${rect.bottom + 8}px`,
    left: `${Math.max(12, rect.right - 148)}px`,
  }
})

const handleDocumentClick = (event) => {
  if (!event.target?.closest?.('.mind-map-download-menu')) {
    exportDownloadOpen.value = false
  }
}

const handleDocumentKeydown = (event) => {
  if (event.key === 'Escape') {
    exportDownloadOpen.value = false
    if (isFullscreen.value) isFullscreen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
  markmapInstance?.destroy?.()
  markmapInstance = null
})
</script>

<template>
  <section :class="['mind-map', { 'mind-map-fullscreen': isFullscreen }]" aria-label="视频总结思维导图">
    <div class="mind-map-heading">
      <h4>{{ labels.title }}</h4>
      <div class="mind-map-toolbar" aria-label="思维导图视图控制">
        <button type="button" @click="fitMindmap">{{ labels.fit }}</button>
        <button type="button" @click="toggleFullscreen">
          {{ isFullscreen ? labels.exitFullscreen : labels.fullscreen }}
        </button>
        <div class="mind-map-download-menu" @click.stop>
          <button ref="downloadButtonRef" type="button" class="download-action" :aria-expanded="exportDownloadOpen" aria-haspopup="menu" @click.stop="toggleExportDownload">
            {{ labels.download }}
            <span class="mind-map-download-arrow" aria-hidden="true"></span>
          </button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="exportDownloadOpen" class="mind-map-download-list" :style="downloadMenuStyle" role="menu" @click.stop>
        <button type="button" role="menuitem" @click.stop="downloadMindMap('png')">
          {{ labels.downloadPng }}
        </button>
        <button type="button" role="menuitem" @click.stop="downloadMindMap('svg')">
          {{ labels.downloadSvg }}
        </button>
      </div>
    </Teleport>

    <div class="mindmap-wrapper">
      <svg ref="mindmapSvg" class="mindmap-svg" />
    </div>
  </section>
</template>

<style scoped>
.mind-map {
  padding: 14px;
  background: #ffffff;
  border: 1px solid #e8eef7;
  border-radius: 10px;
}

.mind-map-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 12px;
}

.mind-map-heading h4 {
  margin: 0;
  color: #111827;
  font-size: 17px;
}

.mind-map-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.mind-map-toolbar button {
  min-width: 72px;
  min-height: 34px;
  padding: 0 12px;
  color: #263247;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  background: #f7faff;
  border: 1px solid #dbe7f7;
  border-radius: 8px;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.mind-map-toolbar button:hover {
  background: #eef5ff;
  border-color: #9fbfff;
}

.mindmap-wrapper {
  position: relative;
  height: min(76vh, 760px);
  min-height: 560px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #edf1f7;
  border-radius: 10px;
}

.mindmap-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.mindmap-wrapper :deep(.markmap-foreign) {
  display: inline-block !important;
}

.mindmap-wrapper :deep(foreignObject) {
  overflow: visible !important;
}

.mindmap-wrapper :deep(foreignObject div) {
  color: #2f3542;
  font: 400 15px/20px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Arial, sans-serif;
}

.mindmap-wrapper :deep(.markmap-node > circle) {
  stroke-width: 1.3px;
}

.mindmap-wrapper :deep(.markmap-link) {
  stroke-linecap: round;
  stroke-linejoin: round;
}

.mind-map-fullscreen {
  position: fixed !important;
  inset: 0;
  z-index: 1000;
  padding: 18px;
  background: #ffffff;
  border: 0;
  border-radius: 0;
}

.mind-map-fullscreen .mindmap-wrapper {
  height: calc(100vh - 82px);
  min-height: 0;
}

@media (max-width: 760px) {
  .mind-map-heading {
    display: grid;
  }

  .mind-map-toolbar {
    justify-content: flex-start;
  }

  .mindmap-wrapper {
    height: 560px;
  }
}

@media (max-width: 520px) {
  .mind-map {
    padding: 12px;
  }

  .mind-map-toolbar button {
    width: 100%;
  }
}
</style>

<style>
.mind-map-download-menu {
  position: relative;
  flex: 0 0 auto;
}

.mind-map-download-menu > button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-width: 92px;
  color: #2563eb !important;
  background: #eef5ff !important;
  border-color: #cfe0ff !important;
}

.mind-map-download-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  border-top: 7px solid #367cff;
  border-right: 6px solid transparent;
  border-left: 6px solid transparent;
}

.mind-map-download-list {
  position: fixed;
  z-index: 5000;
  width: 148px;
  overflow: hidden;
  padding: 6px 0;
  background: #ffffff;
  border: 1px solid #d2def0;
  border-radius: 10px;
  box-shadow: 0 14px 28px rgba(30, 43, 70, 0.18);
}

.mind-map-download-list button {
  display: block;
  width: 100%;
  min-height: 36px;
  padding: 0 16px;
  color: #2563eb;
  font: 750 14px/1 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  text-align: left;
  cursor: pointer;
  background: #ffffff;
  border: 0;
}

.mind-map-download-list button:hover,
.mind-map-download-list button:focus-visible {
  color: #ffffff;
  background: #256fe8;
  outline: none;
}
</style>
