<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  createAiSummaryTask,
  createBiliQrCode,
  createDownloadTask,
  getAiSummaryTask,
  getBiliQrStatus,
  getTask,
  getVideoInfo,
} from './api/client'
import MindMapView from './components/MindMapView.vue'
import SubtitleUploadPanel from './components/SubtitleUploadPanel.vue'
import VideoChatPanel from './components/VideoChatPanel.vue'

const url = ref('')
const urlInput = ref(null)
const cookiesText = ref('')
const useBrowserCookies = ref(false)
const browserCookies = ref('chrome')
const biliSessionId = ref('')
const biliQrImage = ref('')
const biliLoginMessage = ref('')
const biliLoggedIn = ref(false)
const biliLoginLoading = ref(false)
const biliPollTimer = ref(null)
const showBiliAuthPanel = ref(false)
const selectedFormat = ref('best')
const loading = ref(false)
const downloading = ref(false)
const error = ref('')
const info = ref(null)
const task = ref(null)
const pollingTimer = ref(null)
const aiTask = ref(null)
const aiLoading = ref(false)
const aiPollingTimer = ref(null)
const transcriptExpanded = ref(false)
const activeAiTab = ref('summary')
const autoDownloadedTaskId = ref('')
const coverLoadFailed = ref(false)
const selectedTranscriptFormat = ref('txt')
const transcriptDownloadOpen = ref(false)
const BILI_AUTH_STORAGE_KEY = 'saveany:bili-auth-session'

const statusText = computed(() => {
  const map = {
    queued: '排队中',
    starting: '准备中',
    downloading: '下载中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  }
  return map[task.value?.status] || task.value?.status || '待开始'
})

const canSubmit = computed(() => url.value.trim().length > 0 && !loading.value)
const taskInProgress = computed(() =>
  ['queued', 'starting', 'downloading', 'processing'].includes(task.value?.status),
)
const canDownload = computed(() => info.value && selectedFormat.value && !downloading.value && !taskInProgress.value)
const activeAuthSessionId = computed(() => (biliLoggedIn.value ? biliSessionId.value : ''))
const platformWarnings = computed(() => info.value?.warnings || [])
const heroCompact = computed(() => Boolean(info.value && url.value.trim()))
const downloadProgress = computed(() => {
  if (task.value?.status === 'completed') {
    return 100
  }
  const value = Number(task.value?.progress || 0)
  return Math.min(100, Math.max(0, Math.round(value)))
})
const showDownloadProgress = computed(() =>
  ['queued', 'starting', 'downloading', 'processing', 'completed'].includes(task.value?.status),
)
const aiTaskInProgress = computed(() => ['queued', 'extracting', 'summarizing'].includes(aiTask.value?.status))
const aiProgress = computed(() => {
  if (aiTask.value?.status === 'completed' || aiTask.value?.status === 'no_transcript') {
    return 100
  }
  const value = Number(aiTask.value?.progress || 0)
  return Math.min(100, Math.max(0, Math.round(value)))
})
const visibleTranscriptSegments = computed(() => {
  const segments = aiTask.value?.transcript_segments || []
  return transcriptExpanded.value ? segments : segments.slice(0, 10)
})
const transcriptText = computed(() =>
  (aiTask.value?.transcript_segments || [])
    .map((segment) => `[${formatDuration(segment.start)}] ${segment.text}`)
    .join('\n'),
)
const transcriptDownloadFormats = [
  { id: 'txt', label: 'TXT' },
  { id: 'srt', label: 'SRT' },
  { id: 'vtt', label: 'VTT' },
  { id: 'md', label: 'MD' },
  { id: 'json', label: 'JSON' },
]
const aiResultTabs = computed(() => [
  { id: 'summary', label: '总结摘要', icon: '📋' },
  { id: 'transcript', label: '字幕文本', icon: '📜' },
  { id: 'mindmap', label: '思维导图', icon: '🧠' },
  { id: 'chat', label: 'AI 问答', icon: '💬' },
])
const highlightIcons = ['💡', '🧠', '🚀', '🎯', '✨', '📌']
const getHighlightIcon = (index) => highlightIcons[index % highlightIcons.length]
const summaryTitle = computed(() => aiTask.value?.summary?.title || info.value?.title || aiTask.value?.title || '视频总结')
const summaryHighlights = computed(() => (aiTask.value?.summary?.key_points || []).map((point) => splitSummaryPoint(point)))
const summaryOutlineSections = computed(() =>
  (aiTask.value?.summary?.outline || []).map((item, index) => {
    const outlinePoint = splitSummaryPoint(item)
    const relatedPoint = summaryHighlights.value[index]
    const bullets = [outlinePoint.body, relatedPoint?.body, relatedPoint?.title]
      .map((value) => String(value || '').trim())
      .filter((value, valueIndex, values) => value && values.indexOf(value) === valueIndex && value !== outlinePoint.title)
      .slice(0, 3)
    return {
      title: outlinePoint.title || `要点 ${index + 1}`,
      intro: outlinePoint.body,
      bullets,
    }
  }),
)
const summaryMarkdown = computed(() => {
  const summary = aiTask.value?.summary
  if (!summary) {
    return ''
  }

  const lines = [`# ${summaryTitle.value}`, '']
  if (summary.one_sentence) {
    lines.push(`> ${summary.one_sentence}`, '')
  }
  if (summary.key_points?.length) {
    lines.push('## 亮点')
    summary.key_points.forEach((point) => lines.push(`- ${point}`))
    lines.push('')
  }
  if (summary.outline?.length) {
    lines.push('## 章节总结')
    summary.outline.forEach((item, index) => lines.push(`${index + 1}. ${item}`))
    lines.push('')
  }
  if (summary.timeline?.length) {
    lines.push('## 时间轴')
    summary.timeline.forEach((item) => lines.push(`- **${item.time} ${item.title}**：${item.summary}`))
    lines.push('')
  }
  if (summary.keywords?.length) {
    lines.push('## 关键词', summary.keywords.map((item) => `\`${item}\``).join(' '), '')
  }
  if (summary.learning_suggestions?.length) {
    lines.push('## 学习建议')
    summary.learning_suggestions.forEach((item) => lines.push(`- ${item}`))
    lines.push('')
  }
  return lines.join('\n').trimEnd()
})

const isVideoLikeFormat = (format) => {
  const hasVideo = format.vcodec && format.vcodec !== 'none'
  const hasAudio = format.acodec && format.acodec !== 'none'
  const ext = (format.ext || '').toLowerCase()
  return hasVideo || ['mp4', 'webm', 'mkv', 'mov', 'flv'].includes(ext)
}

const getFormatDownloadValue = (format) => {
  const hasVideo = format.vcodec && format.vcodec !== 'none'
  const hasAudio = format.acodec && format.acodec !== 'none'
  if (hasVideo && !hasAudio) {
    return `${format.format_id}+bestaudio/${format.format_id}`
  }
  return format.format_id
}

const getResolutionHeight = (resolution) => {
  const text = String(resolution || '')
  const pair = text.match(/\d+x(\d+)/)
  if (pair) {
    return Number(pair[1])
  }
  return Number(text.match(/(\d+)p?/)?.[1] || 0)
}

const getDisplayResolution = (resolution) => {
  const height = getResolutionHeight(resolution)
  return height ? `${height}p` : resolution || '原始'
}

const getFileSizeText = (format) => {
  const size = format.filesize || format.filesize_approx || format.size
  return size ? `${(size / 1024 / 1024).toFixed(1)}MB` : ''
}

const formatDuration = (seconds) => {
  if (!seconds) {
    return ''
  }
  const total = Math.max(0, Math.round(Number(seconds)))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`
}

const splitSummaryPoint = (value) => {
  const text = String(value || '')
  const parts = text.split(/[：:]/)
  if (parts.length <= 1) {
    return { title: text, body: '' }
  }
  return {
    title: parts[0].trim(),
    body: parts.slice(1).join('：').trim(),
  }
}

const getSafeFilename = (name, fallback = 'video-summary') => {
  const cleaned = String(name || fallback)
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 48)
  return cleaned || fallback
}

const downloadTextFile = (content, filename, type = 'text/plain;charset=utf-8') => {
  const blob = new Blob([content], { type })
  const downloadUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(downloadUrl)
}

const formatSubtitleTimestamp = (seconds, separator = ',') => {
  const totalMs = Math.max(0, Math.round(Number(seconds || 0) * 1000))
  const hours = Math.floor(totalMs / 3600000)
  const minutes = Math.floor((totalMs % 3600000) / 60000)
  const secs = Math.floor((totalMs % 60000) / 1000)
  const ms = totalMs % 1000
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}${separator}${String(ms).padStart(3, '0')}`
}

const getSegmentEnd = (segments, index) => {
  const current = segments[index]
  const next = segments[index + 1]
  const fallbackEnd = Number(current.start || 0) + 3
  const end = Number(current.end || next?.start || fallbackEnd)
  return end > Number(current.start || 0) ? end : fallbackEnd
}

const buildTranscriptContent = (format) => {
  const segments = aiTask.value?.transcript_segments || []
  const title = summaryTitle.value
  if (format === 'json') {
    return JSON.stringify(
      {
        title,
        language: aiTask.value?.transcript_language || '',
        segments,
      },
      null,
      2,
    )
  }
  if (format === 'srt') {
    return segments
      .map((segment, index) => {
        const start = formatSubtitleTimestamp(segment.start, ',')
        const end = formatSubtitleTimestamp(getSegmentEnd(segments, index), ',')
        return `${index + 1}\n${start} --> ${end}\n${segment.text}`
      })
      .join('\n\n')
  }
  if (format === 'vtt') {
    const body = segments
      .map((segment, index) => {
        const start = formatSubtitleTimestamp(segment.start, '.')
        const end = formatSubtitleTimestamp(getSegmentEnd(segments, index), '.')
        return `${index + 1}\n${start} --> ${end}\n${segment.text}`
      })
      .join('\n\n')
    return `WEBVTT\n\n${body}`
  }
  if (format === 'md') {
    return [`# ${title}`, '', `语言：${aiTask.value?.transcript_language || '未知'}`, '', '| 时间 | 字幕 |', '| --- | --- |', ...segments.map((segment) => `| ${formatDuration(segment.start)} | ${String(segment.text || '').replace(/\|/g, '\\|')} |`)].join('\n')
  }
  return segments.map((segment) => `[${formatDuration(segment.start)}] ${segment.text}`).join('\n')
}

const downloadTranscript = (format) => {
  const content = buildTranscriptContent(format)
  const filename = `${getSafeFilename(summaryTitle.value)}-字幕.${format}`
  const type = format === 'json' ? 'application/json;charset=utf-8' : 'text/plain;charset=utf-8'
  downloadTextFile(content, filename, type)
}

const toggleTranscriptDownload = () => {
  transcriptDownloadOpen.value = !transcriptDownloadOpen.value
}

const selectTranscriptDownload = (format) => {
  selectedTranscriptFormat.value = format
  transcriptDownloadOpen.value = false
  downloadTranscript(format)
}

const formatChoices = computed(() => {
  if (!info.value) {
    return []
  }

  const byResolution = new Map()

  for (const format of info.value.formats || []) {
    if (!format.format_id || !isVideoLikeFormat(format)) {
      continue
    }

    const resolution = format.resolution || '原始'
    const height = getResolutionHeight(resolution)
    const key = height || resolution
    const ext = (format.ext || '').toLowerCase()
    const size = format.filesize || format.filesize_approx || 0
    const current = byResolution.get(key)
    const hasVideo = format.vcodec && format.vcodec !== 'none'
    const hasAudio = format.acodec && format.acodec !== 'none'
    const score = (ext === 'mp4' ? 1000000000000 : 0) + size
    const currentScore = current
      ? ((current.ext || '').toLowerCase() === 'mp4' ? 1000000000000 : 0) + (current.filesize || current.filesize_approx || 0)
      : -1

    if (!current || score > currentScore) {
      byResolution.set(key, format)
    }
  }

  return Array.from(byResolution.values())
    .filter((format) => format.format_id)
    .filter((format) => isVideoLikeFormat(format))
    .map((format) => {
      const hasVideo = format.vcodec && format.vcodec !== 'none'
      const hasAudio = format.acodec && format.acodec !== 'none'
      const size = format.filesize || format.filesize_approx
      const sizeText = size ? `${(size / 1024 / 1024).toFixed(1)}MB` : '大小未知'
      const resolution = getDisplayResolution(format.resolution)
      const ext = format.ext ? format.ext.toUpperCase() : '格式'
      const typeText = hasVideo && !hasAudio ? '视频+音频合并' : hasVideo && hasAudio ? '视频+音频' : '视频'

      return {
        id: getFormatDownloadValue(format),
        title: `${resolution} ${ext} (${typeText}${size ? `, ${sizeText}` : ''})`,
        meta: `${format.ext || 'media'} · ${hasAudio ? '含音频' : '自动合并音频'}`,
        resolution,
        size: size || 0,
        hasAudio,
        hasVideo,
        height: getResolutionHeight(format.resolution),
      }
    })
    .sort((a, b) => {
      return b.height - a.height || b.size - a.size
    })
    .map((format, index) => ({
      ...format,
      title:
        index === 0
          ? `${format.resolution} 最佳（${format.hasAudio ? '视频+音频' : '视频+音频合并'}${format.size ? `, ${(format.size / 1024 / 1024).toFixed(1)}MB` : ''}）`
          : format.title,
    }))
    .slice(0, 6)
})

const resetResult = () => {
  error.value = ''
  info.value = null
  task.value = null
  aiTask.value = null
  selectedFormat.value = ''
  autoDownloadedTaskId.value = ''
  transcriptExpanded.value = false
  activeAiTab.value = 'summary'
  coverLoadFailed.value = false
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
  if (aiPollingTimer.value) {
    window.clearInterval(aiPollingTimer.value)
    aiPollingTimer.value = null
  }
}

const clearUrl = () => {
  url.value = ''
  showBiliAuthPanel.value = false
  urlInput.value?.focus()
}

const isBiliUrl = (value) => /(^|\.)bilibili\.com|(^|\.)b23\.tv/i.test(String(value || ''))

const triggerFileDownload = (downloadUrl, taskId) => {
  if (!downloadUrl || autoDownloadedTaskId.value === taskId) {
    return
  }
  autoDownloadedTaskId.value = taskId
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = ''
  link.rel = 'noreferrer'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const parseInfo = async () => {
  const requestUrl = url.value.trim()
  showBiliAuthPanel.value = isBiliUrl(requestUrl)
  resetResult()
  loading.value = true
  try {
    info.value = await getVideoInfo(
      requestUrl,
      cookiesText.value.trim(),
      useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : '',
      activeAuthSessionId.value,
    )
    selectedFormat.value = formatChoices.value[0]?.id || ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const pollTask = (taskId) => {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
  }
  pollingTimer.value = window.setInterval(async () => {
    try {
      task.value = await getTask(taskId)
      if (['completed', 'failed'].includes(task.value.status)) {
        window.clearInterval(pollingTimer.value)
        pollingTimer.value = null
        if (task.value.status === 'completed') {
          triggerFileDownload(task.value.download_url, task.value.task_id)
        }
      }
    } catch (err) {
      error.value = err.message
      window.clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }, 1200)
}

const pollAiSummaryTask = (taskId) => {
  if (aiPollingTimer.value) {
    window.clearInterval(aiPollingTimer.value)
  }
  aiPollingTimer.value = window.setInterval(async () => {
    try {
      aiTask.value = await getAiSummaryTask(taskId)
      if (['completed', 'failed', 'no_transcript'].includes(aiTask.value.status)) {
        window.clearInterval(aiPollingTimer.value)
        aiPollingTimer.value = null
      }
    } catch (err) {
      error.value = err.message
      window.clearInterval(aiPollingTimer.value)
      aiPollingTimer.value = null
    }
  }, 1400)
}

const startAiSummary = async () => {
  if (!info.value || aiLoading.value || aiTaskInProgress.value) {
    return
  }
  error.value = ''
  aiLoading.value = true
  transcriptExpanded.value = false
  activeAiTab.value = 'summary'
  aiTask.value = null
  try {
    const created = await createAiSummaryTask({
      url: url.value.trim(),
      cookies: cookiesText.value.trim() || null,
      browser_cookies: useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : null,
      auth_session_id: activeAuthSessionId.value || null,
    })
    aiTask.value = created
    pollAiSummaryTask(created.task_id)
  } catch (err) {
    error.value = err.message
  } finally {
    aiLoading.value = false
  }
}

const handleSubtitleSummaryCreated = (created) => {
  aiTask.value = created
  transcriptExpanded.value = false
  activeAiTab.value = 'summary'
  pollAiSummaryTask(created.task_id)
}

const copyTranscript = async () => {
  if (!transcriptText.value) {
    return
  }
  try {
    await window.navigator.clipboard.writeText(transcriptText.value)
  } catch {
    error.value = '复制失败，请手动选择字幕内容复制'
  }
}

const copySummaryMarkdown = async () => {
  if (!summaryMarkdown.value) {
    return
  }
  try {
    await window.navigator.clipboard.writeText(summaryMarkdown.value)
  } catch {
    error.value = '复制失败，请手动选择总结内容复制'
  }
}

const downloadSummaryMarkdown = () => {
  if (!summaryMarkdown.value) {
    return
  }
  downloadTextFile(summaryMarkdown.value, `${getSafeFilename(summaryTitle.value)}-总结.md`, 'text/markdown;charset=utf-8')
}

const downloadSelected = async () => {
  if (!canDownload.value) {
    return
  }
  error.value = ''
  task.value = null
  downloading.value = true
  try {
    const created = await createDownloadTask({
      url: url.value.trim(),
      format: selectedFormat.value,
      with_subtitle: false,
      cookies: cookiesText.value.trim() || null,
      browser_cookies: useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : null,
      auth_session_id: activeAuthSessionId.value || null,
    })
    task.value = created
    pollTask(created.task_id)
  } catch (err) {
    error.value = err.message
  } finally {
    downloading.value = false
  }
}

const rememberBiliSession = (sessionId) => {
  if (!sessionId) {
    return
  }
  window.localStorage.setItem(BILI_AUTH_STORAGE_KEY, sessionId)
}

const forgetBiliSession = () => {
  window.localStorage.removeItem(BILI_AUTH_STORAGE_KEY)
}

onMounted(async () => {
  const storedSessionId = window.localStorage.getItem(BILI_AUTH_STORAGE_KEY)
  if (!storedSessionId) {
    return
  }
  try {
    const status = await getBiliQrStatus(storedSessionId)
    if (status.is_logged_in) {
      biliSessionId.value = storedSessionId
      biliLoggedIn.value = true
      biliLoginMessage.value = '已恢复 Bilibili 登录态'
      return
    }
    forgetBiliSession()
  } catch {
    forgetBiliSession()
  }
})

onBeforeUnmount(() => {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
  }
  if (biliPollTimer.value) {
    window.clearInterval(biliPollTimer.value)
  }
  if (aiPollingTimer.value) {
    window.clearInterval(aiPollingTimer.value)
  }
})

const startBiliLogin = async () => {
  biliLoginLoading.value = true
  biliLoginMessage.value = ''
  biliLoggedIn.value = false
  forgetBiliSession()
  if (biliPollTimer.value) {
    window.clearInterval(biliPollTimer.value)
    biliPollTimer.value = null
  }
  try {
    const result = await createBiliQrCode()
    biliSessionId.value = result.session_id
    biliQrImage.value = result.qrcode_image
    biliLoginMessage.value = '请使用哔哩哔哩 App 扫码登录'
    biliPollTimer.value = window.setInterval(async () => {
      try {
        const status = await getBiliQrStatus(result.session_id)
        biliLoginMessage.value = status.message
        biliLoggedIn.value = status.is_logged_in
        if (status.is_logged_in) {
          rememberBiliSession(result.session_id)
          window.clearInterval(biliPollTimer.value)
          biliPollTimer.value = null
        }
      } catch (err) {
        biliLoginMessage.value = err.message
      }
    }, 1800)
  } catch (err) {
    biliLoginMessage.value = err.message
  } finally {
    biliLoginLoading.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <header class="topbar">
      <a class="brand" href="#console">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" role="img">
            <path d="M9.75 8.5 15.5 12l-5.75 3.5v-7Z" />
            <rect x="4.5" y="4.5" width="15" height="15" rx="5.5" />
          </svg>
        </span>
        <span class="brand-name">SaveAny</span>
        <span class="brand-badge">万能视频下载</span>
      </a>
      <nav class="nav-links" aria-label="主导航">
        <a href="#features">功能特性</a>
        <a href="#pricing">套餐价格</a>
        <a href="#platforms">支持平台</a>
      </nav>
      <button class="vip-button" type="button" aria-label="开通 VIP">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.9-5.4 2.9 1-6-4.4-4.3 6.1-.9L12 3Z" />
        </svg>
        开通 VIP
      </button>
    </header>

    <main>
      <section id="console" :class="['hero', { 'has-result': info, compact: heroCompact }]">
        <span v-if="!heroCompact" class="support-pill">
          <span></span>
          支持 1800+ 平台，永久免费使用
        </span>

        <div v-if="!heroCompact" class="hero-copy">
          <h1>万能视频下载器，<em>一键保存</em></h1>
          <p class="subtitle">
            粘贴视频链接，智能解析，支持多种清晰度下载。YouTube、Bilibili、抖音、TikTok...
            随时随地，想下就下
          </p>
        </div>

        <section class="search-card" aria-label="视频下载控制台">
          <div class="search-bar">
            <label class="sr-only" for="video-url">视频链接</label>
            <svg class="link-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M10.5 13.5 13.5 10.5" />
              <path d="M8.25 15.75 6.8 17.2a3.4 3.4 0 0 1-4.8-4.8l3-3a3.4 3.4 0 0 1 4.8 0" />
              <path d="M15.75 8.25 17.2 6.8a3.4 3.4 0 0 1 4.8 4.8l-3 3a3.4 3.4 0 0 1-4.8 0" />
            </svg>
            <input
              id="video-url"
              ref="urlInput"
              v-model="url"
              class="url-input"
              type="url"
              placeholder="https://www.youtube.com/watch?v=... 粘贴视频链接"
              @keyup.enter="parseInfo"
            />
            <button
              v-if="url"
              class="clear-url-button"
              type="button"
              aria-label="清空视频链接"
              title="清空"
              @click="clearUrl"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
            <button class="primary-button" :disabled="!canSubmit" type="button" @click="parseInfo">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m16.5 16.5 4 4" />
              </svg>
              {{ loading ? '解析中...' : '解析视频' }}
            </button>
          </div>

          <div v-if="!heroCompact" class="quick-row">
            <span>试试：</span>
            <button type="button">YouTube</button>
            <button type="button">Bilibili</button>
            <button type="button">Twitter/X</button>
          </div>

          <div v-if="showBiliAuthPanel" class="bili-auth-panel">
            <button class="bili-auth-trigger" type="button" :disabled="biliLoginLoading" @click="startBiliLogin">
              {{ biliLoginLoading ? '正在生成登录二维码...' : biliLoggedIn ? '已登录 Bilibili' : '解析不到 1080P？扫码登录 Bilibili' }}
            </button>
            <div v-if="biliQrImage || biliLoginMessage" class="bili-login-box">
              <img v-if="biliQrImage && !biliLoggedIn" class="bili-qr" :src="biliQrImage" alt="Bilibili 登录二维码" />
              <span v-if="biliLoginMessage" :class="['bili-login-message', { success: biliLoggedIn }]">
                {{ biliLoginMessage }}
              </span>
            </div>
          </div>
        </section>
      </section>

      <p v-if="error" class="alert" role="alert">{{ error }}</p>

      <section v-if="info" class="result-panel" aria-label="解析结果">
        <div class="download-card">
          <article class="video-summary">
            <div class="cover-wrap">
              <img
                v-if="(info.thumbnail_proxy_url || info.thumbnail) && !coverLoadFailed"
                :src="info.thumbnail_proxy_url || info.thumbnail"
                alt="视频封面"
                @error="coverLoadFailed = true"
              />
              <div v-else class="thumbnail-empty"></div>
              <span v-if="info.duration" class="duration-badge">{{ formatDuration(info.duration) }}</span>
            </div>
            <div class="summary-copy">
              <h2>{{ info.title || '未命名视频' }}</h2>
              <p class="meta-line">
                {{ info.uploader || '未知作者' }}
                <span class="source-chip">{{ info.extractor || 'Unknown' }}</span>
                <span v-if="info.duration">时长 {{ formatDuration(info.duration) }}</span>
              </p>
              <p v-if="platformWarnings.length" class="platform-warning">
                {{ platformWarnings[0] }}
              </p>
            </div>
          </article>

          <div class="format-section">
            <h3>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 7h16" />
                <path d="M7 12h10" />
                <path d="M10 17h4" />
              </svg>
              选择清晰度和格式
            </h3>
            <div class="format-grid">
              <button
                v-for="format in formatChoices"
                :key="format.id + format.title"
                :class="{ active: selectedFormat === format.id }"
                class="format-card"
                type="button"
                @click="selectedFormat = format.id"
              >
                <span class="format-icon">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <rect x="5" y="5" width="14" height="14" rx="2" />
                    <path d="M9 9h2v2H9zM13 9h2v2h-2zM9 13h2v2H9zM13 13h2v2h-2z" />
                  </svg>
                </span>
                <span>
                  <strong>{{ format.title }}</strong>
                  <small>{{ format.meta }}</small>
                </span>
              </button>
            </div>
          </div>

          <div class="download-footer">
            <button class="download-button" :disabled="!canDownload" type="button" @click="downloadSelected">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 4v10" />
                <path d="m7 10 5 5 5-5" />
                <path d="M5 20h14" />
              </svg>
              {{ downloading || taskInProgress ? '正在下载' : '立即下载' }}
            </button>
            <button class="ai-summary-button" :disabled="aiLoading || aiTaskInProgress" type="button" @click="startAiSummary">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3v4" />
                <path d="M12 17v4" />
                <path d="M3 12h4" />
                <path d="M17 12h4" />
                <path d="m6.5 6.5 2.8 2.8" />
                <path d="m14.7 14.7 2.8 2.8" />
                <path d="m17.5 6.5-2.8 2.8" />
                <path d="m9.3 14.7-2.8 2.8" />
              </svg>
              {{ aiTaskInProgress ? '总结中' : aiTask?.status === 'completed' ? '重新总结' : 'AI 总结' }}
            </button>
            <span
              v-if="aiTask && ['queued', 'extracting', 'summarizing', 'completed'].includes(aiTask.status)"
              class="progress-ring ai-progress-ring"
              :style="{ '--progress': `${aiProgress}%` }"
              aria-label="AI 总结进度"
              aria-live="polite"
            >
              <span>{{ aiProgress }}%</span>
            </span>
            <span
              v-if="showDownloadProgress"
              class="progress-ring"
              :style="{ '--progress': `${downloadProgress}%` }"
              aria-live="polite"
            >
              <span>{{ downloadProgress }}%</span>
            </span>
            <span class="selected-hint">
              {{ selectedFormat ? `已选择：${formatChoices.find((item) => item.id === selectedFormat)?.title}` : '暂无可下载格式' }}
            </span>
          </div>

          <p v-if="task?.status === 'failed'" class="download-error">{{ task.error }}</p>
          <p v-else-if="task?.download_url" class="download-success">下载已完成，已自动开始保存到本地。</p>
        </div>

        <section class="ai-summary-panel" aria-label="AI 视频总结">
          <div v-if="aiTask" :class="['ai-task-state', { warning: aiTask.status === 'no_transcript' }]" aria-live="polite">
            <p v-if="aiTask.status === 'no_transcript'" class="ai-empty-state">
              当前视频没有可提取的平台字幕或自动字幕。后续可接入音频转写，或支持上传 SRT/VTT 字幕后总结。
            </p>
            <SubtitleUploadPanel
              v-if="aiTask.status === 'no_transcript'"
              :title="info?.title || ''"
              :url="url.trim()"
              @created="handleSubtitleSummaryCreated"
              @error="error = $event"
            />
            <p v-else-if="aiTask.status === 'failed'" class="download-error">{{ aiTask.error }}</p>
          </div>

          <div v-if="aiTask?.summary" class="ai-result-tabs">
            <div class="ai-tab-list" role="tablist" aria-label="AI 生成结果">
              <button
                v-for="tab in aiResultTabs"
                :id="`ai-tab-${tab.id}`"
                :key="tab.id"
                :aria-controls="`ai-panel-${tab.id}`"
                :aria-selected="activeAiTab === tab.id"
                :class="{ active: activeAiTab === tab.id }"
                type="button"
                role="tab"
                @click="activeAiTab = tab.id"
              >
                <span class="ai-tab-icon" aria-hidden="true">{{ tab.icon }}</span>
                <span>{{ tab.label }}</span>
              </button>
            </div>

            <div class="ai-tab-panel-shell">
              <section
                v-show="activeAiTab === 'summary'"
                id="ai-panel-summary"
                class="ai-tab-panel ai-summary-result"
                role="tabpanel"
                aria-labelledby="ai-tab-summary"
              >
                <article class="ai-doc-panel">
                  <header class="ai-doc-toolbar">
                    <h1 class="sr-only">{{ summaryTitle }}</h1>
                    <div class="ai-doc-actions" aria-label="总结导出操作">
                      <button class="text-action-button" type="button" @click="copySummaryMarkdown">复制 MD</button>
                      <button class="text-action-button" type="button" @click="downloadSummaryMarkdown">下载 MD</button>
                    </div>
                  </header>

                  <section class="ai-doc-section ai-doc-overview">
                    <h2>视频概述</h2>
                    <p>{{ aiTask.summary.one_sentence }}</p>
                  </section>

                  <section v-if="summaryOutlineSections.length" class="ai-doc-section ai-doc-outline">
                    <h2>内容大纲</h2>
                    <ol>
                      <li v-for="(item, index) in summaryOutlineSections" :key="`${item.title}-${index}`">
                        <strong>{{ item.title }}</strong>
                        <p v-if="item.intro">{{ item.intro }}</p>
                        <ul v-if="item.bullets.length">
                          <li v-for="bullet in item.bullets" :key="bullet">{{ bullet }}</li>
                        </ul>
                      </li>
                    </ol>
                  </section>

                  <section v-if="summaryHighlights.length" class="ai-doc-section ai-doc-points">
                    <h2>核心要点</h2>
                    <ul>
                      <li v-for="(point, index) in summaryHighlights" :key="`${point.title}-${index}`">
                        <strong>{{ point.title }}</strong>
                        <template v-if="point.body">：{{ point.body }}</template>
                      </li>
                    </ul>
                  </section>

                  <section v-if="aiTask.summary.keywords?.length" class="ai-doc-section">
                    <h2>关键词</h2>
                    <p class="ai-doc-keywords">
                      <span v-for="keyword in aiTask.summary.keywords" :key="keyword">{{ keyword }}</span>
                    </p>
                  </section>

                  <section v-if="aiTask.summary.learning_suggestions?.length" class="ai-doc-section">
                    <h2>学习建议</h2>
                    <ul class="ai-doc-list">
                      <li v-for="item in aiTask.summary.learning_suggestions" :key="item">{{ item }}</li>
                    </ul>
                  </section>
                </article>
              </section>

              <section
                v-show="activeAiTab === 'transcript'"
                id="ai-panel-transcript"
                class="ai-tab-panel transcript-panel"
                role="tabpanel"
                aria-labelledby="ai-tab-transcript"
              >
                <div class="transcript-header">
                  <div>
                    <h4>字幕文本</h4>
                    <p>
                      共 {{ aiTask.transcript_segments.length }} 条字幕
                      <span class="transcript-language">{{ aiTask.transcript_language || '未知语言' }}</span>
                    </p>
                  </div>
                  <div class="transcript-actions" aria-label="字幕操作">
                    <button class="text-action-button" type="button" @click="copyTranscript">复制全文</button>
                    <div class="download-menu">
                      <button
                        class="text-action-button download-menu-trigger"
                        type="button"
                        :aria-expanded="transcriptDownloadOpen"
                        aria-haspopup="menu"
                        @click="toggleTranscriptDownload"
                      >
                        下载
                        <span class="download-menu-arrow" aria-hidden="true"></span>
                      </button>
                      <div v-if="transcriptDownloadOpen" class="download-menu-list" role="menu">
                        <button
                          v-for="format in transcriptDownloadFormats"
                          :key="format.id"
                          type="button"
                          role="menuitem"
                          @click="selectTranscriptDownload(format.id)"
                        >
                          {{ format.label }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="transcript-list">
                  <p v-for="segment in aiTask.transcript_segments" :key="`${segment.start}-${segment.text}`">
                    <time>{{ formatDuration(segment.start) }}</time>
                    <span>{{ segment.text }}</span>
                  </p>
                </div>
              </section>

              <section
                v-show="activeAiTab === 'mindmap'"
                id="ai-panel-mindmap"
                class="ai-tab-panel"
                role="tabpanel"
                aria-labelledby="ai-tab-mindmap"
              >
                <MindMapView v-if="activeAiTab === 'mindmap'" :summary="aiTask.summary" />
              </section>

              <section
                v-show="activeAiTab === 'chat'"
                id="ai-panel-chat"
                class="ai-tab-panel"
                role="tabpanel"
                aria-labelledby="ai-tab-chat"
              >
                <VideoChatPanel v-if="activeAiTab === 'chat'" :task-id="aiTask.task_id" />
              </section>
            </div>
          </div>
        </section>
      </section>

      <section id="features" class="feature-section">
        <span id="platforms" class="section-anchor" aria-hidden="true"></span>
        <div class="section-heading">
          <h2>为什么选择 <span>SaveAny</span></h2>
          <p>简单、快速、强大的视频下载体验</p>
        </div>
        <div class="feature-grid">
          <article>
            <span class="feature-icon globe">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="8" />
                <path d="M4 12h16M12 4c2 2.4 3 5.1 3 8s-1 5.6-3 8M12 4c-2 2.4-3 5.1-3 8s1 5.6 3 8" />
              </svg>
            </span>
            <h3>支持 1800+ 平台</h3>
            <p>YouTube、Bilibili、抖音、TikTok、Twitter、Instagram 等全球主流平台。</p>
          </article>
          <article>
            <span class="feature-icon lightning">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M13 3 6 13h5l-1 8 8-12h-5l1-6Z" />
              </svg>
            </span>
            <h3>极速解析下载</h3>
            <p>智能解析视频链接，自动匹配最优下载方式，减少等待步骤。</p>
          </article>
          <article>
            <span class="feature-icon mobile">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="7" y="3" width="10" height="18" rx="2.5" />
                <path d="M11 17h2" />
              </svg>
            </span>
            <h3>手机也能用</h3>
            <p>适配手机浏览器，随时粘贴链接，无需安装任何 App。</p>
          </article>
          <article>
            <span class="feature-icon quality">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 5h14v14H5z" />
                <path d="M8 9h8M8 13h5" />
                <path d="m15 14 2 2 3-4" />
              </svg>
            </span>
            <h3>多种清晰度</h3>
            <p>支持从 360p 到 4K 多种清晰度选择，满足不同场景需求。</p>
          </article>
          <article>
            <span class="feature-icon ai">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="5" y="6" width="14" height="12" rx="3" />
                <path d="M9 6V4M15 6V4M9 18v2M15 18v2M8.5 11h.01M15.5 11h.01M10 15h4" />
              </svg>
            </span>
            <h3>AI 视频总结</h3>
            <p>AI 智能分析视频内容，一键生成摘要、思维导图和视频问答。</p>
          </article>
        </div>
      </section>

      <section id="pricing" class="pricing-section">
        <div class="section-heading">
          <h2>选择适合你的方案</h2>
          <p>免费版满足日常使用，VIP 解锁全部高级功能</p>
        </div>
        <div class="plan-grid">
          <article class="plan-card free-plan">
            <div>
              <h3>免费版</h3>
              <p>满足基础下载需求</p>
            </div>
            <p class="plan-price"><strong>¥0</strong><span>/永久</span></p>
            <ul>
              <li>每日 5 次免费下载</li>
              <li>最高支持 720p 清晰度</li>
              <li>支持 1800+ 平台</li>
              <li>基础视频信息解析</li>
            </ul>
            <button type="button" class="plan-button muted">当前方案</button>
          </article>

          <article class="plan-card vip-plan">
            <span class="recommend-badge">推荐</span>
            <div>
              <h3>VIP 高级版</h3>
              <p>解锁全部功能，无限制使用</p>
            </div>
            <p class="plan-price"><strong>¥9.9</strong><span>/月</span><em>限时优惠</em></p>
            <ul>
              <li>无限次下载，无任何限制</li>
              <li>最高支持 4K / 8K 画质</li>
              <li>批量下载，一键搞定</li>
              <li>字幕下载与翻译</li>
              <li>AI 视频内容总结</li>
              <li>专属客服优先支持</li>
            </ul>
            <button type="button" class="plan-button primary">立即开通 VIP</button>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>
