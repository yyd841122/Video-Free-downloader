<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true,
  },
})

const ROOT = { x: 96, width: 190, height: 58 }
const TOPIC = { x: 456, width: 168, height: 44 }
const LEAF = { x: 688, width: 560, height: 30 }
const MAP_PADDING = 72
const BRANCH_GAP = 112
const LEAF_GAP = 42
const MIN_SCALE = 0.2
const MAX_SCALE = 1.7

const viewportRef = ref(null)
const scale = ref(0.82)
const offsetX = ref(24)
const offsetY = ref(24)
const isPanning = ref(false)
const dragStart = ref({ x: 0, y: 0, offsetX: 0, offsetY: 0 })

const limitItems = (items, limit = 5) => (Array.isArray(items) ? items.filter(Boolean).slice(0, limit) : [])
const branchColors = ['#ff6258', '#a83bd5', '#31b64b', '#3f8fe6', '#e6a51c']

const splitNodeText = (value) => {
  const text = String(value || '').trim()
  const match = text.match(/^([^：:]{2,14})[：:]\s*(.+)$/)
  if (match) {
    return {
      label: match[1],
      text: match[2],
    }
  }
  return {
    label: '',
    text,
  }
}

const branches = computed(() => [
  {
    id: 'outline',
    title: '章节大纲',
    items: limitItems(props.summary.outline, 6).map(splitNodeText),
  },
  {
    id: 'points',
    title: '核心要点',
    items: limitItems(props.summary.key_points, 6).map(splitNodeText),
  },
  {
    id: 'timeline',
    title: '时间轴',
    items: limitItems(props.summary.timeline, 6).map((item) => ({
      label: item.time,
      text: `${item.title}：${item.summary}`,
    })),
  },
  {
    id: 'keywords',
    title: '关键词',
    items: limitItems(props.summary.keywords, 8).map(splitNodeText),
  },
  {
    id: 'suggestions',
    title: '学习建议',
    items: limitItems(props.summary.learning_suggestions, 4).map(splitNodeText),
  },
]
  .filter((branch) => branch.items.length)
  .map((branch, index) => ({
    ...branch,
    color: branchColors[index % branchColors.length],
  })))

const rootTitle = computed(() => props.summary.title || '视频内容')
const compactRootTitle = computed(() => {
  const source = String(props.summary.one_sentence || rootTitle.value || '视频内容').trim()
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
  if (matchedTopic) {
    return matchedTopic
  }
  const cleaned = source
    .replace(/^本视频(?:主要)?(?:讲解|介绍|总结|分析|评测|讨论|围绕|关于)?/g, '')
    .replace(/^视频(?:主要)?(?:讲解|介绍|总结|分析|评测|讨论|围绕|关于)?/g, '')
    .replace(/^通过.+?(?:介绍|讲解|分析|评测)/g, '')
    .replace(/#\S+/g, '')
    .replace(/[｜|].*$/g, '')
    .replace(/[，,：:；;].*$/g, '')
    .replace(/^(了|的|和|对|从|以|为|关于|围绕)/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return (cleaned || String(rootTitle.value || '视频内容')).slice(0, 18)
})

const layout = computed(() => {
  let cursor = MAP_PADDING
  const rows = branches.value.map((branch) => {
    const height = Math.max(86, (branch.items.length - 1) * LEAF_GAP + 42)
    const centerY = cursor + height / 2
    const leafStartY = centerY - ((branch.items.length - 1) * LEAF_GAP) / 2
    const leaves = branch.items.map((item, index) => ({
      ...item,
      x: LEAF.x,
      y: leafStartY + index * LEAF_GAP,
    }))
    cursor += height + BRANCH_GAP
    return {
      ...branch,
      x: TOPIC.x,
      y: centerY,
      leaves,
    }
  })
  const height = Math.max(560, cursor - BRANCH_GAP + MAP_PADDING)
  const rootY = height / 2
  const width = LEAF.x + LEAF.width + MAP_PADDING
  return {
    width,
    height,
    root: {
      x: ROOT.x,
      y: rootY,
      width: ROOT.width,
      height: ROOT.height,
    },
    rows,
  }
})

const stageStyle = computed(() => ({
  width: `${layout.value.width}px`,
  height: `${layout.value.height}px`,
  transform: `translate(${offsetX.value}px, ${offsetY.value}px) scale(${scale.value})`,
}))

const zoomPercent = computed(() => `${Math.round(scale.value * 100)}%`)

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const getBranchPath = (row) => {
  const startX = layout.value.root.x + layout.value.root.width
  const startY = layout.value.root.y
  const endX = row.x
  const endY = row.y
  return `M ${startX} ${startY} C ${startX + 92} ${startY}, ${endX - 112} ${endY}, ${endX} ${endY}`
}

const getLeafPath = (row, leaf) => {
  const startX = row.x + TOPIC.width
  const startY = row.y
  const endX = leaf.x
  const endY = leaf.y
  return `M ${startX} ${startY} C ${startX + 44} ${startY}, ${endX - 62} ${endY}, ${endX} ${endY}`
}

const fitToView = () => {
  const viewport = viewportRef.value
  if (!viewport) return
  const rect = viewport.getBoundingClientRect()
  const nextScale = clamp(Math.min((rect.width - 40) / layout.value.width, (rect.height - 40) / layout.value.height, 1), MIN_SCALE, MAX_SCALE)
  scale.value = Number(nextScale.toFixed(2))
  offsetX.value = Math.round((rect.width - layout.value.width * scale.value) / 2)
  offsetY.value = Math.round((rect.height - layout.value.height * scale.value) / 2)
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
  <section v-if="branches.length" class="mind-map" aria-label="视频总结思维导图">
    <div class="mind-map-heading">
      <div>
        <h4>思维导图</h4>
        <p>像 XMind 一样拖动画布、滚轮缩放，快速扫读视频知识结构。</p>
      </div>
      <div class="mind-map-toolbar" aria-label="思维导图视图控制">
        <button type="button" aria-label="缩小思维导图" @click="zoomBy(-0.12)">-</button>
        <span>{{ zoomPercent }}</span>
        <button type="button" aria-label="放大思维导图" @click="zoomBy(0.12)">+</button>
        <button type="button" @click="fitToView">适配</button>
        <button type="button" @click="resetView">重置</button>
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
        <svg class="mind-map-lines" :viewBox="`0 0 ${layout.width} ${layout.height}`" aria-hidden="true" focusable="false">
          <g v-for="row in layout.rows" :key="`${row.id}-lines`">
            <path class="mind-branch-line" :d="getBranchPath(row)" :stroke="row.color" />
            <path
              v-for="(leaf, index) in row.leaves"
              :key="`${row.id}-leaf-line-${index}`"
              class="mind-leaf-line"
              :d="getLeafPath(row, leaf)"
              :stroke="row.color"
            />
          </g>
        </svg>

        <article
          class="mind-root"
          :style="{
            left: `${layout.root.x}px`,
            top: `${layout.root.y - layout.root.height / 2}px`,
            width: `${layout.root.width}px`,
          }"
        >
          <strong>{{ compactRootTitle }}</strong>
        </article>

        <template v-for="row in layout.rows" :key="row.id">
          <article
            class="mind-topic"
            :style="{
              '--node-color': row.color,
              left: `${row.x}px`,
              top: `${row.y - TOPIC.height / 2}px`,
              width: `${TOPIC.width}px`,
            }"
          >
            {{ row.title }}
          </article>

          <article
            v-for="(leaf, index) in row.leaves"
            :key="`${row.id}-${index}`"
            class="mind-leaf"
            :style="{
              '--node-color': row.color,
              left: `${leaf.x}px`,
              top: `${leaf.y - LEAF.height / 2}px`,
              width: `${LEAF.width}px`,
            }"
          >
            <span v-if="leaf.label" class="mind-leaf-label">{{ leaf.label }}</span>
            <span class="mind-leaf-text">{{ leaf.text }}</span>
          </article>
        </template>
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
  color: #1b202a;
}

.mind-map-heading p {
  margin: 7px 0 0;
  color: #7f8b9c;
  line-height: 1.6;
}

.mind-map-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.mind-map-toolbar button,
.mind-map-toolbar span {
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

.mind-map-toolbar span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  color: #367cff;
  background: #eef5ff;
}

.mind-map-viewport {
  position: relative;
  height: min(72vh, 680px);
  min-height: 460px;
  overflow: hidden;
  cursor: grab;
  touch-action: none;
  user-select: none;
  background:
    radial-gradient(circle at 1px 1px, #dfe8f5 1px, transparent 0) 0 0 / 22px 22px,
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e3ebf6;
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

.mind-map-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.mind-branch-line,
.mind-leaf-line {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.mind-branch-line {
  stroke-width: 6;
}

.mind-leaf-line {
  stroke-width: 2.2;
}

.mind-root,
.mind-topic,
.mind-leaf {
  position: absolute;
  z-index: 2;
  box-sizing: border-box;
  background: #ffffff;
}

.mind-root {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 58px;
  padding: 10px 14px;
  background: #eef5ff;
  border: 2px solid #aebccd;
  border-radius: 8px;
  box-shadow: 0 14px 30px rgba(54, 124, 255, 0.1);
}

.mind-root strong {
  display: -webkit-box;
  overflow: hidden;
  color: #1b202a;
  font-size: 16px;
  line-height: 1.4;
  text-align: center;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.mind-topic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 8px 14px;
  color: #111827;
  font-weight: 900;
  line-height: 1.35;
  text-align: center;
  border: 2px solid var(--node-color);
  border-radius: 8px;
}

.mind-leaf {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  min-height: 30px;
  padding: 0 0 5px;
  color: #263a55;
  line-height: 1.45;
  border-bottom: 2px solid color-mix(in srgb, var(--node-color) 78%, white);
}

.mind-leaf-label {
  padding-right: 14px;
  color: #111827;
  font-size: 14px;
  font-weight: 900;
  white-space: nowrap;
}

.mind-leaf-text {
  min-width: 0;
  color: #243650;
  font-size: 14px;
  overflow-wrap: anywhere;
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
  .mind-map-toolbar span {
    min-height: 38px;
  }
}
</style>
