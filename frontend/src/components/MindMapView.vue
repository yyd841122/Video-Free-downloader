<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true,
  },
})

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
        root: 'Video Summary',
        empty: 'Mind map content was not generated. Please run AI Summary again.',
      }
    : {
        title: '思维导图',
        fit: '适配',
        fullscreen: '全屏',
        exitFullscreen: '退出全屏',
        download: '下载',
        downloadPng: '高清 PNG',
        downloadSvg: 'SVG',
        root: '视频总结',
        empty: '思维导图内容未生成，请重新运行 AI 总结。',
      },
)

const getSafeFilename = (name, fallback = 'mind-map') => {
  const cleaned = String(name || fallback)
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 48)
  return cleaned || fallback
}

const mindmapMarkdown = computed(() => String(props.summary.mindmap_markdown || '').trim())

const renderMindmap = async () => {
  await nextTick()
  if (!mindmapSvg.value) return
  mindmapSvg.value.innerHTML = ''
  if (!mindmapMarkdown.value) return
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

const EXPORT_FONT_SIZE = 16
const EXPORT_LINE_HEIGHT = 22
const EXPORT_FONT_FAMILY = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif'
const EXPORT_FONT = `500 ${EXPORT_FONT_SIZE}px ${EXPORT_FONT_FAMILY}`

const measureExportText = (() => {
  let context
  return (text) => {
    if (!context) {
      const canvas = document.createElement('canvas')
      context = canvas.getContext('2d')
    }
    if (!context) return String(text || '').length * EXPORT_FONT_SIZE * 0.55
    context.font = EXPORT_FONT
    return context.measureText(String(text || '')).width
  }
})()

const wrapExportText = (text, maxWidth) => {
  const value = cleanText(text)
  if (!value) return []
  const width = Math.max(120, maxWidth)
  const tokens = containsCjk(value) ? Array.from(value) : value.split(/(\s+)/).filter(Boolean)
  const lines = []
  let current = ''

  tokens.forEach((token) => {
    const next = current ? `${current}${token}` : token.trimStart()
    if (current && measureExportText(next) > width) {
      lines.push(current.trim())
      current = token.trimStart()
      return
    }
    current = next
  })

  if (current.trim()) lines.push(current.trim())
  return lines.length ? lines : [value]
}

const buildExportableSvg = () => {
  if (!mindmapSvg.value) return
  const cloned = mindmapSvg.value.cloneNode(true)
  cloned.querySelectorAll('[transform]').forEach((element) => {
    const transform = element.getAttribute('transform')
    if (transform?.includes('NaN')) {
      element.setAttribute('transform', 'translate(0,0) scale(1)')
    }
  })
  const rootGroup = cloned.querySelector('g')
  rootGroup?.removeAttribute('transform')
  cloned.querySelectorAll('foreignObject').forEach((foreignObject) => {
    const textContent = foreignObject.textContent?.trim() || ''
    if (!textContent) {
      foreignObject.remove()
      return
    }
    const x = Number.parseFloat(foreignObject.getAttribute('x') || '0') || 0
    const y = Number.parseFloat(foreignObject.getAttribute('y') || '0') || 0
    const w = Number.parseFloat(foreignObject.getAttribute('width') || '360') || 360
    const h = Number.parseFloat(foreignObject.getAttribute('height') || '20') || 20
    const lines = wrapExportText(textContent, w - 12)
    const textElement = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    textElement.setAttribute('x', String(x + 4))
    textElement.setAttribute('y', String(y + Math.max(15, (h - (lines.length - 1) * EXPORT_LINE_HEIGHT) / 2)))
    textElement.setAttribute('font-size', String(EXPORT_FONT_SIZE))
    textElement.setAttribute('font-family', EXPORT_FONT_FAMILY)
    textElement.setAttribute('fill', '#1f2937')
    textElement.setAttribute('font-weight', '500')
    textElement.setAttribute('dominant-baseline', 'central')
    lines.forEach((line, index) => {
      const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan')
      tspan.setAttribute('x', String(x + 4))
      tspan.setAttribute('dy', index === 0 ? '0' : String(EXPORT_LINE_HEIGHT))
      tspan.textContent = line
      textElement.appendChild(tspan)
    })
    foreignObject.parentNode?.replaceChild(textElement, foreignObject)
  })
  cloned.querySelectorAll('.markmap-link, path.markmap-link').forEach((path) => {
    const depth = Number.parseInt(path.getAttribute('data-depth') || '3', 10)
    path.setAttribute('fill', 'none')
    path.setAttribute('stroke-linecap', 'round')
    path.setAttribute('stroke-linejoin', 'round')
    path.setAttribute('stroke-width', depth <= 2 ? '1.35' : depth === 3 ? '1.05' : '0.85')
    if (!path.getAttribute('stroke') || path.getAttribute('stroke') === 'currentColor') {
      path.setAttribute('stroke', '#64748b')
    }
  })
  cloned.querySelectorAll('.markmap-node line').forEach((line) => {
    const parent = line.closest('.markmap-node')
    const depth = Number.parseInt(parent?.getAttribute('data-depth') || '3', 10)
    line.setAttribute('stroke-width', depth <= 2 ? '1.2' : depth === 3 ? '0.95' : '0.8')
    line.setAttribute('stroke-linecap', 'round')
    if (!line.getAttribute('stroke') || line.getAttribute('stroke') === 'currentColor') {
      line.setAttribute('stroke', '#94a3b8')
    }
  })
  cloned.querySelectorAll('.markmap-node > circle').forEach((circle) => {
    circle.setAttribute('r', '4.2')
    circle.setAttribute('stroke-width', '1')
    circle.setAttribute('fill', '#ffffff')
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

const getTranslateValues = (transform = '') => {
  const match = transform.match(/translate\(\s*([-\d.e]+)(?:[,\s]+([-\d.e]+))?\s*\)/)
  return {
    x: match ? Number.parseFloat(match[1]) || 0 : 0,
    y: match ? Number.parseFloat(match[2]) || 0 : 0,
  }
}

const expandExportBounds = (bounds, x, y) => {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return
  bounds.minX = Math.min(bounds.minX, x)
  bounds.minY = Math.min(bounds.minY, y)
  bounds.maxX = Math.max(bounds.maxX, x)
  bounds.maxY = Math.max(bounds.maxY, y)
}

const getFallbackContentBBox = (svgElement) => {
  const bounds = {
    minX: Number.POSITIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
  }

  svgElement.querySelectorAll('path[d]').forEach((path) => {
    const values = (path.getAttribute('d') || '').match(/-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi) || []
    for (let index = 0; index < values.length - 1; index += 2) {
      expandExportBounds(bounds, Number.parseFloat(values[index]), Number.parseFloat(values[index + 1]))
    }
  })

  svgElement.querySelectorAll('.markmap-node').forEach((node) => {
    const offset = getTranslateValues(node.getAttribute('transform') || '')
    node.querySelectorAll('line').forEach((line) => {
      const x1 = Number.parseFloat(line.getAttribute('x1') || '0') + offset.x
      const y1 = Number.parseFloat(line.getAttribute('y1') || '0') + offset.y
      const x2 = Number.parseFloat(line.getAttribute('x2') || '0') + offset.x
      const y2 = Number.parseFloat(line.getAttribute('y2') || '0') + offset.y
      expandExportBounds(bounds, x1, y1)
      expandExportBounds(bounds, x2, y2)
    })
    node.querySelectorAll('circle').forEach((circle) => {
      const cx = Number.parseFloat(circle.getAttribute('cx') || '0') + offset.x
      const cy = Number.parseFloat(circle.getAttribute('cy') || '0') + offset.y
      const r = Number.parseFloat(circle.getAttribute('r') || '0') + 2
      expandExportBounds(bounds, cx - r, cy - r)
      expandExportBounds(bounds, cx + r, cy + r)
    })
    node.querySelectorAll('text').forEach((text) => {
      const x = Number.parseFloat(text.getAttribute('x') || '0') + offset.x
      const y = Number.parseFloat(text.getAttribute('y') || '0') + offset.y
      const lineCount = Math.max(1, text.querySelectorAll('tspan').length || 1)
      const lineWidths = Array.from(text.querySelectorAll('tspan')).map((tspan) => measureExportText(tspan.textContent || ''))
      const width = Math.max(measureExportText(text.textContent || ''), ...lineWidths, 80)
      expandExportBounds(bounds, x, y - EXPORT_LINE_HEIGHT)
      expandExportBounds(bounds, x + width + 16, y + lineCount * EXPORT_LINE_HEIGHT)
    })
  })

  if (![bounds.minX, bounds.minY, bounds.maxX, bounds.maxY].every(Number.isFinite)) {
    return { x: -60, y: -60, width: 1440, height: 1080 }
  }

  return {
    x: bounds.minX,
    y: bounds.minY,
    width: bounds.maxX - bounds.minX,
    height: bounds.maxY - bounds.minY,
  }
}

const getContentBBox = (targetSvg = mindmapSvg.value) => {
  const svgElement = targetSvg
  if (!svgElement) return { x: 0, y: 0, width: 1200, height: 800 }
  const wasConnected = svgElement.isConnected
  let host
  if (!wasConnected) {
    host = document.createElement('div')
    host.style.cssText = 'position:absolute;left:-100000px;top:-100000px;width:1px;height:1px;overflow:visible;opacity:0;pointer-events:none;'
    svgElement.setAttribute('viewBox', '-10000 -10000 20000 20000')
    svgElement.setAttribute('width', '20000')
    svgElement.setAttribute('height', '20000')
    host.appendChild(svgElement)
    document.body.appendChild(host)
  }
  const rootGroup = svgElement.querySelector('g')
  try {
    if (rootGroup) {
      try {
        const bbox = rootGroup.getBBox()
        if (bbox.width > 0 && bbox.height > 0) {
          return {
            x: bbox.x,
            y: bbox.y,
            width: bbox.width,
            height: bbox.height,
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
    return getFallbackContentBBox(svgElement)
  } finally {
    if (host) {
      host.remove()
    }
  }
}

const setFullViewBox = (svgClone) => {
  const dims = getContentBBox(svgClone)
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
      <p v-if="!mindmapMarkdown" class="mindmap-empty">{{ labels.empty }}</p>
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

.mindmap-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  padding: 24px;
  color: #64748b;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
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
