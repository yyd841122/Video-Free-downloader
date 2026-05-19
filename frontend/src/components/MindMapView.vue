<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true,
  },
})

const MIN_SCALE = 0.24
const MAX_SCALE = 1.7
const PNG_EXPORT_SCALE = 3
const MAP_PADDING = 72
const ROW_GAP = 18
const CHILD_GAP = 26
const DOT_GRID = 22

const DEPTH = [
  { x: 56, maxChars: 12, fontSize: 13, weight: 700, endOffset: 170 },
  { x: 286, maxChars: 8, fontSize: 14, weight: 850, endOffset: 145 },
  { x: 520, maxChars: 16, fontSize: 13.5, weight: 760, endOffset: 184 },
  { x: 790, maxChars: 34, fontSize: 13, weight: 520, endOffset: 600 },
]

const branchColors = ['#df7b37', '#7ba85d', '#72a8b7', '#c96f90', '#9b7a9a']
const exportDownloadFormats = [
  { id: 'png', label: '高清 PNG' },
  { id: 'svg', label: 'SVG' },
]

const viewportRef = ref(null)
const scale = ref(0.82)
const offsetX = ref(24)
const offsetY = ref(24)
const exportDownloadOpen = ref(false)
const isPanning = ref(false)
const dragStart = ref({ x: 0, y: 0, offsetX: 0, offsetY: 0 })

const cleanText = (value) =>
  String(value || '')
    .replace(/^\s*\d+[.、)\-]\s*/, '')
    .replace(/\s+/g, ' ')
    .trim()

const comparableText = (value) => cleanText(value).replace(/[^\p{L}\p{N}]/gu, '').toLowerCase()

const isSameMeaning = (a, b) => {
  const left = comparableText(a)
  const right = comparableText(b)
  if (!left || !right) return false
  if (left === right) return true
  return (left.length > 12 && right.includes(left)) || (right.length > 12 && left.includes(right))
}

const uniqueTextItems = (items, limit = 8) => {
  const seen = []
  const result = []
  for (const item of items || []) {
    const text = cleanText(item)
    if (!text || seen.some((value) => isSameMeaning(value, text))) continue
    seen.push(text)
    result.push(text)
    if (result.length >= limit) break
  }
  return result
}

const splitClauses = (value, limit = 3) =>
  uniqueTextItems(
    cleanText(value)
      .split(/[。；;]\s*|，\s*/)
      .map(cleanText)
      .filter((item) => item.length >= 4),
    limit,
  )

const parseSummaryNode = (value) => {
  const text = cleanText(value)
  const match = text.match(/^([^：:]{2,22})[：:]\s*(.+)$/)
  if (match) {
    return buildContentNode(cleanText(match[1]), cleanText(match[2]))
  }
  const parts = text.split(/[。；;]\s*|，\s*/).map(cleanText).filter(Boolean)
  if (parts.length > 1) {
    return buildContentNode(parts[0], parts.slice(1).join('，'))
  }
  return buildContentNode(text, '')
}

const buildContentNode = (title, body) => {
  const cleanTitle = cleanText(title)
  const cleanBody = cleanText(body)
  const clauses = splitClauses(cleanBody, 3).filter((item) => !isSameMeaning(item, cleanTitle))
  const children = clauses.length >= 2 ? clauses.map((item) => ({ title: item, children: [] })) : []
  const displayTitle = cleanBody && children.length === 0 && !isSameMeaning(cleanTitle, cleanBody) ? `${cleanTitle}：${cleanBody}` : cleanTitle
  return {
    title: displayTitle,
    children,
  }
}

const rootTitle = computed(() => props.summary.title || '视频内容')
const compactRootTitle = computed(() => {
  const source = cleanText(props.summary.one_sentence || rootTitle.value || '视频内容')
  const keywordText = Array.isArray(props.summary.keywords) ? props.summary.keywords.join(' ') : ''
  const combined = `${source} ${keywordText}`
  const topicRules = [
    { pattern: /AI\s*编程工具|AI编程工具|编程工具/i, topic: 'AI编程工具评测' },
    { pattern: /AI\s*编程|AI编程/i, topic: 'AI编程实践' },
    { pattern: /视频下载|下载器|下载工具/i, topic: '视频下载工具' },
    { pattern: /字幕|转录|转写/i, topic: '字幕转录总结' },
    { pattern: /学习|复习|知识点/i, topic: '视频学习要点' },
  ]
  const matchedTopic = topicRules.find((rule) => rule.pattern.test(combined))?.topic
  if (matchedTopic) return matchedTopic
  const cleaned = source
    .replace(/^本视频(?:主要)?(?:讲解|介绍|总结|分析|评测|讨论|围绕|关于)?/g, '')
    .replace(/^视频(?:主要)?(?:讲解|介绍|总结|分析|评测|讨论|围绕|关于)?/g, '')
    .replace(/#\S+/g, '')
    .replace(/[｜|，,：:；;].*$/g, '')
    .trim()
  return (cleaned || String(rootTitle.value || '视频内容')).slice(0, 18)
})

const buildGroup = (id, title, children, minChildren = 1) => {
  const deduped = []
  for (const child of children) {
    if (!child?.title) continue
    if (deduped.some((item) => isSameMeaning(item.title, child.title))) continue
    deduped.push(child)
  }
  return deduped.length >= minChildren ? { id, title, children: deduped } : null
}

const mindTree = computed(() => {
  const outlineNodes = uniqueTextItems(props.summary.outline || [], 6).map(parseSummaryNode)
  const pointNodes = uniqueTextItems(props.summary.key_points || [], 6).map(parseSummaryNode)
  const overviewChildren = [
    buildContentNode('核心主题', props.summary.one_sentence || rootTitle.value),
    props.summary.audience ? buildContentNode('适合人群', props.summary.audience) : null,
  ].filter(Boolean)

  const children = [
    buildGroup('overview', '视频概述', overviewChildren),
    buildGroup('outline', '内容大纲', outlineNodes),
    buildGroup('points', '核心观点', pointNodes),
  ].filter(Boolean)

  return {
    id: 'root',
    title: compactRootTitle.value,
    children,
  }
})

const wrapText = (value, maxLength) => {
  const text = cleanText(value)
  if (!text) return ['']
  const chunks = []
  let cursor = 0
  while (cursor < text.length) {
    chunks.push(text.slice(cursor, cursor + maxLength))
    cursor += maxLength
  }
  return chunks.slice(0, 3)
}

const getNodeMetrics = (title, depth, hasChildren = false) => {
  const config = DEPTH[Math.min(depth, DEPTH.length - 1)]
  const leafMaxChars = depth >= 2 ? 34 : Math.max(config.maxChars, 18)
  const leafEndOffset = depth >= 2 ? 420 : Math.max(config.endOffset, 220)
  const maxChars = hasChildren ? config.maxChars : leafMaxChars
  const endOffset = hasChildren ? config.endOffset : leafEndOffset
  const lines = wrapText(title, maxChars)
  const height = Math.max(28, lines.length * 17 + 8)
  const width = Math.min(endOffset, Math.max(54, Math.max(...lines.map((line) => line.length)) * config.fontSize + 16))
  return {
    ...config,
    maxChars,
    endOffset,
    lines,
    height,
    width,
  }
}

const treeLayout = computed(() => {
  const nodes = []
  const links = []
  let nodeId = 0

  const measure = (node, depth, color) => {
    const sourceChildren = node.children || []
    const metrics = getNodeMetrics(node.title, depth, sourceChildren.length > 0)
    const children = sourceChildren.map((child) => measure(child, depth + 1, color))
    const childrenHeight = children.reduce((sum, child) => sum + child.subtreeHeight, 0) + Math.max(0, children.length - 1) * CHILD_GAP
    return {
      ...node,
      id: `${depth}-${nodeId++}`,
      depth,
      color,
      children,
      metrics,
      subtreeHeight: children.length ? Math.max(metrics.height, childrenHeight) : metrics.height,
    }
  }

  const root = measure(mindTree.value, 0, '#7c8da5')
  let maxX = 0
  let maxY = 0

  const place = (node, top) => {
    const config = DEPTH[Math.min(node.depth, DEPTH.length - 1)]
    const x = config.x
    let y
    if (node.children.length) {
      const childrenTotal = node.children.reduce((sum, child) => sum + child.subtreeHeight, 0) + Math.max(0, node.children.length - 1) * CHILD_GAP
      let childTop = top + (node.subtreeHeight - childrenTotal) / 2
      node.children.forEach((child) => {
        place(child, childTop)
        childTop += child.subtreeHeight + CHILD_GAP
      })
      y = (node.children[0].y + node.children[node.children.length - 1].y) / 2
    } else {
      y = top + node.subtreeHeight / 2
    }

    node.x = x
    node.y = y
    node.endX = x + node.metrics.width
    nodes.push(node)
    maxX = Math.max(maxX, node.depth >= 3 ? x + 620 : node.endX + 60)
    maxY = Math.max(maxY, y + node.metrics.height / 2)

    const linkFan = Math.min(18, Math.max(7, node.metrics.height * 0.42))
    const linkMiddle = (node.children.length - 1) / 2
    node.children.forEach((child, index) => {
      const fanOffset = node.children.length > 1 ? ((index - linkMiddle) / linkMiddle) * linkFan : 0
      links.push({
        id: `${node.id}-${child.id}`,
        color: child.color || node.color,
        fromX: node.endX + (node.depth <= 1 ? 10 : 14),
        fromY: node.y + fanOffset,
        toX: child.x - 14,
        toY: child.y,
        strokeWidth: node.depth <= 1 ? 1.45 : 1.15,
        opacity: node.depth <= 1 ? 0.82 : 0.68,
      })
    })
  }

  const coloredRoot = {
    ...root,
    children: root.children.map((child, index) => ({
      ...child,
      color: branchColors[index % branchColors.length],
      children: child.children.map((grandChild) => ({
        ...grandChild,
        color: branchColors[index % branchColors.length],
        children: grandChild.children.map((leaf) => ({
          ...leaf,
          color: branchColors[index % branchColors.length],
        })),
      })),
    })),
  }

  place(coloredRoot, MAP_PADDING)

  return {
    nodes,
    links,
    width: Math.max(1160, maxX + MAP_PADDING),
    height: Math.max(620, maxY + MAP_PADDING),
  }
})

const stageStyle = computed(() => ({
  width: `${treeLayout.value.width}px`,
  height: `${treeLayout.value.height}px`,
  transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${scale.value})`,
}))

const zoomPercent = computed(() => `${Math.round(scale.value * 100)}%`)

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const getLinkPath = (link) => {
  const dx = Math.max(64, (link.toX - link.fromX) * 0.46)
  return `M ${link.fromX} ${link.fromY} C ${link.fromX + dx} ${link.fromY}, ${link.toX - dx} ${link.toY}, ${link.toX} ${link.toY}`
}

const fitToView = () => {
  const viewport = viewportRef.value
  if (!viewport) return
  const rect = viewport.getBoundingClientRect()
  const nextScale = clamp(Math.min((rect.width - 44) / treeLayout.value.width, (rect.height - 44) / treeLayout.value.height, 1), MIN_SCALE, MAX_SCALE)
  scale.value = Number(nextScale.toFixed(2))
  offsetX.value = Math.round((rect.width - treeLayout.value.width * scale.value) / 2)
  offsetY.value = Math.round((rect.height - treeLayout.value.height * scale.value) / 2)
}

const resetView = () => {
  scale.value = 0.82
  offsetX.value = 24
  offsetY.value = 24
}

const zoomTo = (nextScale, clientX, clientY) => {
  const viewport = viewportRef.value
  if (!viewport) return
  const rect = viewport.getBoundingClientRect()
  const x = clientX ?? rect.left + rect.width / 2
  const y = clientY ?? rect.top + rect.height / 2
  const mapX = (x - rect.left - offsetX.value) / scale.value
  const mapY = (y - rect.top - offsetY.value) / scale.value
  const clampedScale = clamp(nextScale, MIN_SCALE, MAX_SCALE)
  offsetX.value = x - rect.left - mapX * clampedScale
  offsetY.value = y - rect.top - mapY * clampedScale
  scale.value = Number(clampedScale.toFixed(2))
}

const zoomBy = (delta) => {
  zoomTo(scale.value + delta)
}

const escapeXml = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const renderSvgText = ({ x, y, lines, color = '#1f2937', size = 14, weight = 600, anchor = 'start', lineHeight = 1.35 }) => {
  const safeLines = lines.map(escapeXml)
  const startDy = safeLines.length > 1 ? -((safeLines.length - 1) * size * lineHeight) / 2 : 0
  return `
    <text x="${x}" y="${y}" text-anchor="${anchor}" dominant-baseline="middle" fill="${color}" font-size="${size}" font-weight="${weight}">
      ${safeLines.map((line, index) => `<tspan x="${x}" dy="${index === 0 ? startDy : size * lineHeight}">${line}</tspan>`).join('')}
    </text>
  `
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

const getExportFilename = (extension) => {
  const source = String(rootTitle.value || compactRootTitle.value || 'mind-map')
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 36)
  return `${source || 'mind-map'}-思维导图.${extension}`
}

const createSvgString = () => {
  const { width, height, nodes, links } = treeLayout.value
  const paths = links
    .map(
      (link) =>
        `<path d="${getLinkPath(link)}" stroke="${link.color}" stroke-width="${link.strokeWidth}" opacity="${link.opacity}" class="mind-link" />`,
    )
    .join('')
  const nodeMarkup = nodes
    .map((node) => {
      const color = node.depth === 0 ? '#516070' : node.color
      const text = renderSvgText({
        x: node.x,
        y: node.y,
        lines: node.metrics.lines,
        color: node.depth <= 2 ? '#1f2937' : '#475569',
        size: node.metrics.fontSize,
        weight: node.metrics.weight,
      })
      const underline = node.depth === 0 ? '' : `<line x1="${node.x}" y1="${node.y + node.metrics.height / 2}" x2="${node.depth >= 3 ? node.x + 560 : node.endX + 18}" y2="${node.y + node.metrics.height / 2}" stroke="${color}" stroke-width="1.2" opacity="0.58" />`
      const dot = node.depth >= 1 && node.children.length ? `<circle cx="${node.endX + 13}" cy="${node.y}" r="4.5" fill="#ffffff" stroke="${color}" stroke-width="1.5" />` : ''
      return `${underline}${text}${dot}`
    })
    .join('')

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <pattern id="dot-grid" x="0" y="0" width="${DOT_GRID}" height="${DOT_GRID}" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="#dfe8f5" />
    </pattern>
    <style>
      text { font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Arial, sans-serif; }
      .mind-link { fill: none; stroke-linecap: round; stroke-linejoin: round; }
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#ffffff" />
  <rect width="100%" height="100%" fill="url(#dot-grid)" opacity="0.55" />
  ${paths}
  ${nodeMarkup}
</svg>`
}

const downloadSvg = () => {
  downloadBlob(new Blob([createSvgString()], { type: 'image/svg+xml;charset=utf-8' }), getExportFilename('svg'))
}

const downloadPng = async () => {
  const svg = createSvgString()
  const { width, height } = treeLayout.value
  const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)
  const image = new Image()
  image.decoding = 'async'
  const loaded = new Promise((resolve, reject) => {
    image.onload = resolve
    image.onerror = reject
  })
  image.src = url
  await loaded
  const canvas = document.createElement('canvas')
  canvas.width = width * PNG_EXPORT_SCALE
  canvas.height = height * PNG_EXPORT_SCALE
  const context = canvas.getContext('2d')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  URL.revokeObjectURL(url)
  canvas.toBlob((blob) => {
    if (blob) downloadBlob(blob, getExportFilename('png'))
  }, 'image/png')
}

const downloadMindMap = (format) => {
  if (format === 'svg') {
    downloadSvg()
    return
  }
  downloadPng()
}

const toggleExportDownload = () => {
  exportDownloadOpen.value = !exportDownloadOpen.value
}

const selectExportDownload = (format) => {
  exportDownloadOpen.value = false
  downloadMindMap(format)
}

const handleWheel = (event) => {
  const direction = event.deltaY > 0 ? -0.08 : 0.08
  zoomTo(scale.value + direction, event.clientX, event.clientY)
}

const handlePointerDown = (event) => {
  if (event.button !== 0) return
  isPanning.value = true
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    offsetX: offsetX.value,
    offsetY: offsetY.value,
  }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

const handlePointerMove = (event) => {
  if (!isPanning.value) return
  offsetX.value = dragStart.value.offsetX + event.clientX - dragStart.value.x
  offsetY.value = dragStart.value.offsetY + event.clientY - dragStart.value.y
}

const stopPanning = (event) => {
  isPanning.value = false
  if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
    event.currentTarget.releasePointerCapture(event.pointerId)
  }
}

onMounted(() => {
  nextTick(fitToView)
  window.addEventListener('resize', fitToView)
})

onUnmounted(() => {
  window.removeEventListener('resize', fitToView)
})

watch(
  () => props.summary,
  () => nextTick(fitToView),
  { deep: true },
)
</script>

<template>
  <section v-if="mindTree.children.length" class="mind-map" aria-label="视频总结思维导图">
    <div class="mind-map-heading">
      <h4>思维导图</h4>
      <div class="mind-map-toolbar" aria-label="思维导图视图控制">
        <button type="button" aria-label="缩小思维导图" @click="zoomBy(-0.12)">-</button>
        <span>{{ zoomPercent }}</span>
        <button type="button" aria-label="放大思维导图" @click="zoomBy(0.12)">+</button>
        <button type="button" @click="fitToView">适配</button>
        <button type="button" @click="resetView">重置</button>
        <div class="mind-map-download-menu">
          <button type="button" :aria-expanded="exportDownloadOpen" aria-haspopup="menu" @click="toggleExportDownload">
            下载
            <span class="mind-map-download-arrow" aria-hidden="true"></span>
          </button>
          <div v-if="exportDownloadOpen" class="mind-map-download-list" role="menu">
            <button v-for="format in exportDownloadFormats" :key="format.id" type="button" role="menuitem" @click="selectExportDownload(format.id)">
              {{ format.label }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      ref="viewportRef"
      class="mind-map-viewport"
      :class="{ 'is-panning': isPanning }"
      role="application"
      aria-label="可拖动缩放的视频内容脑图"
      tabindex="0"
      @wheel.prevent="handleWheel"
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="stopPanning"
      @pointercancel="stopPanning"
      @pointerleave="stopPanning"
    >
      <div class="mind-map-stage" :style="stageStyle">
        <svg class="mind-map-canvas" :viewBox="`0 0 ${treeLayout.width} ${treeLayout.height}`" aria-hidden="true" focusable="false">
          <defs>
            <pattern id="mind-dot-grid" x="0" y="0" :width="DOT_GRID" :height="DOT_GRID" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="#dfe8f5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="#ffffff" />
          <rect width="100%" height="100%" fill="url(#mind-dot-grid)" opacity="0.55" />
          <path
            v-for="link in treeLayout.links"
            :key="link.id"
            class="mind-link"
            :d="getLinkPath(link)"
            :stroke="link.color"
            :stroke-width="link.strokeWidth"
            :opacity="link.opacity"
            vector-effect="non-scaling-stroke"
          />
          <g v-for="node in treeLayout.nodes" :key="node.id" class="mind-node">
            <line
              v-if="node.depth > 0"
              :x1="node.x"
              :y1="node.y + node.metrics.height / 2"
              :x2="node.depth >= 3 ? node.x + 560 : node.endX + 18"
              :y2="node.y + node.metrics.height / 2"
              :stroke="node.color"
              stroke-width="1.2"
              opacity="0.58"
            />
            <text
              :x="node.x"
              :y="node.y"
              dominant-baseline="middle"
              :fill="node.depth <= 2 ? '#1f2937' : '#475569'"
              :font-size="node.metrics.fontSize"
              :font-weight="node.metrics.weight"
            >
              <tspan
                v-for="(line, index) in node.metrics.lines"
                :key="`${node.id}-${index}`"
                :x="node.x"
                :dy="index === 0 ? (node.metrics.lines.length > 1 ? -((node.metrics.lines.length - 1) * node.metrics.fontSize * 1.35) / 2 : 0) : node.metrics.fontSize * 1.35"
              >
                {{ line }}
              </tspan>
            </text>
            <circle
              v-if="node.depth >= 1 && node.children.length"
              :cx="node.endX + 13"
              :cy="node.y"
              r="4.5"
              fill="#ffffff"
              :stroke="node.color"
              stroke-width="1.5"
            />
          </g>
        </svg>
      </div>
    </div>
  </section>
</template>

<style scoped>
.mind-map {
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e8eef7;
  border-radius: 8px;
}

.mind-map-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
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

.mind-map-toolbar button,
.mind-map-toolbar > span {
  min-width: 42px;
  min-height: 34px;
  padding: 0 12px;
  color: #263247;
  font-size: 13px;
  font-weight: 800;
  background: #f7faff;
  border: 1px solid #dbe7f7;
  border-radius: 8px;
}

.mind-map-toolbar button {
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.mind-map-toolbar button:hover {
  background: #eef5ff;
  border-color: #9fbfff;
}

.mind-map-toolbar button:active {
  transform: scale(0.96);
}

.mind-map-toolbar > span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  color: #367cff;
  background: #eef5ff;
}

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
}

.mind-map-download-arrow {
  display: inline-block;
  flex: 0 0 auto;
  width: 0;
  height: 0;
  min-width: 0;
  min-height: 0;
  padding: 0;
  background: transparent;
  border-top: 7px solid #367cff;
  border-right: 6px solid transparent;
  border-left: 6px solid transparent;
  border-radius: 0;
}

.mind-map-download-list {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 20;
  min-width: 130px;
  overflow: hidden;
  padding: 6px 0;
  background: #ffffff;
  border: 1px solid #d2def0;
  border-radius: 10px;
  box-shadow: 0 14px 28px rgba(30, 43, 70, 0.14);
}

.mind-map-download-list button {
  display: block;
  width: 100%;
  min-height: 34px;
  padding: 0 16px;
  color: #2563eb;
  font-size: 14px;
  font-weight: 750;
  text-align: left;
  background: #ffffff;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.mind-map-download-list button:hover,
.mind-map-download-list button:focus-visible {
  color: #ffffff;
  background: #256fe8;
  border-color: transparent;
  outline: none;
}

.mind-map-viewport {
  position: relative;
  height: min(72vh, 680px);
  min-height: 460px;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
  user-select: none;
  border: 1px solid #dbe8fb;
  border-radius: 8px;
}

.mind-map-viewport:focus {
  outline: 3px solid rgba(54, 124, 255, 0.22);
  outline-offset: 2px;
}

.mind-map-viewport.is-panning {
  cursor: grabbing;
}

.mind-map-stage {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  transition: transform 0.12s ease-out;
}

.mind-map-viewport.is-panning .mind-map-stage {
  transition: none;
}

.mind-map-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.mind-link {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  shape-rendering: geometricPrecision;
}

.mind-node text {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Arial, sans-serif;
}

@media (max-width: 760px) {
  .mind-map-heading {
    display: grid;
  }

  .mind-map-toolbar {
    justify-content: flex-start;
  }

  .mind-map-viewport {
    height: 560px;
  }
}

@media (max-width: 520px) {
  .mind-map {
    padding: 14px;
  }

  .mind-map-toolbar button,
  .mind-map-toolbar > span {
    min-height: 38px;
  }

  .mind-map-download-menu,
  .mind-map-download-menu > button {
    width: 100%;
  }

  .mind-map-download-list {
    right: auto;
    left: 0;
  }
}
</style>
