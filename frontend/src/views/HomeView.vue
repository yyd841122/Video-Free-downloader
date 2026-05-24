<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  createAiSummaryTask,
  createBiliQrCode,
  createBatchDownload,
  createDownloadTask,
  getAiSummaryTask,
  getBiliQrStatus,
  getTask,
  getVideoInfo,
  resolveApiUrl,
} from '../api/client'
import MindMapView from '../components/MindMapView.vue'
import SubtitleUploadPanel from '../components/SubtitleUploadPanel.vue'
import VideoChatPanel from '../components/VideoChatPanel.vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()

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
const biliAuthPanelEl = ref(null)
const showYouTubeAuthPanel = ref(false)
const youtubeAuthPanelEl = ref(null)
const youtubeCookiesDraft = ref('')
const youtubeCookieFileInput = ref(null)
const youtubeAuthMessage = ref('')
const youtubeCookieAdvancedOpen = ref(false)
// 用户提交 YouTube Cookie 后自动续解析（对齐 B 站 pendingParseAfterLogin）。
const pendingParseAfterYouTubeAuth = ref(false)
// 标记"扫码登录成功后要继续解析视频"。
// 触发场景：用户粘贴 B 站链接但还没登录态，前端不直接调 /api/video/info（避免后端被 WAF 撞 412），
// 而是先自动弹码，扫成功后通过这个 flag 自动重试 parseInfo。
const pendingParseAfterLogin = ref(false)
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
const aiProgressTimer = ref(null)
const displayAiProgress = ref(0)
const transcriptExpanded = ref(false)
const activeAiTab = ref('summary')
const downloadedTaskIds = ref(new Set())
const batchPollTimers = ref([])
const batchOpen = ref(false)
const batchUrlsText = ref('')
const batchLoading = ref(false)
const batchResults = ref([])
const BATCH_ACTIVE_STATUSES = ['queued', 'starting', 'downloading', 'processing']
const coverLoadFailed = ref(false)
const selectedTranscriptFormat = ref('txt')
const transcriptDownloadOpen = ref(false)
const BILI_AUTH_STORAGE_KEY = 'saveany:bili-auth-session'

const statusText = computed(() => {
  const key = task.value?.status
  if (key && t(`home.taskStatus.${key}`)) {
    return t(`home.taskStatus.${key}`)
  }
  return task.value?.status || t('home.taskStatus.default')
})

const taskInProgress = computed(() =>
  ['queued', 'starting', 'downloading', 'processing'].includes(task.value?.status),
)
const aiTaskInProgress = computed(() => ['queued', 'extracting', 'summarizing'].includes(aiTask.value?.status))
const parseLocked = computed(() => loading.value || downloading.value || taskInProgress.value || aiLoading.value || aiTaskInProgress.value)
const canSubmit = computed(() => url.value.trim().length > 0 && !parseLocked.value)
const canDownload = computed(() => info.value && selectedFormat.value && !downloading.value && !taskInProgress.value)
const activeAuthSessionId = computed(() => (biliLoggedIn.value ? biliSessionId.value : ''))

const batchTrackRows = computed(() => batchResults.value.filter((row) => row.task_id && !row.error))

const batchInProgress = computed(
  () => batchLoading.value || batchTrackRows.value.some((row) => BATCH_ACTIVE_STATUSES.includes(row.status)),
)

const batchProgressPercent = computed(() => {
  const rows = batchTrackRows.value
  if (!rows.length) return 0
  const sum = rows.reduce((acc, row) => {
    if (row.status === 'completed' || row.status === 'failed') {
      return acc + 100
    }
    return acc + Math.min(100, Math.max(0, Math.round(Number(row.progress) || 0)))
  }, 0)
  return Math.min(100, Math.round(sum / rows.length))
})
const platformWarnings = computed(() => info.value?.warnings || [])
// 后端在 JSON 里返回的 thumbnail_proxy_url 是 "/api/proxy/<token>" 这种相对路径，
// 浏览器原生 <img> 不走 fetch、不会自动拼上后端 API 域名，
// 会按"当前页面域名"解析 → 命中 Cloudflare Pages SPA fallback → 拿到 index.html 当图片解析失败。
// 因此这里显式 resolveApiUrl 把相对路径拼成后端绝对地址，再让 <img> 去取。
// 非代理的 info.thumbnail 通常是平台 CDN 绝对地址（http(s)://...），resolveApiUrl 会原样返回。
const coverImageUrl = computed(() => {
  const proxy = info.value?.thumbnail_proxy_url
  if (proxy) {
    return resolveApiUrl(proxy)
  }
  return info.value?.thumbnail || ''
})
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
const aiProgress = computed(() => {
  if (aiTask.value?.status === 'completed' || aiTask.value?.status === 'no_transcript') {
    return 100
  }
  const value = displayAiProgress.value || aiTask.value?.progress || 0
  return Math.min(100, Math.max(0, Math.round(value)))
})
const transcriptSegments = computed(() => aiTask.value?.transcript_segments || [])
const aiStatusMessage = computed(() => String(aiTask.value?.message || ''))
const aiNoTranscriptMessage = computed(() => {
  const message = aiStatusMessage.value
  if (/转写|语音|ASR|生成字幕|transcri|speech|subtitle/i.test(message)) {
    return t('home.noTranscriptAsrFailed')
  }
  return t('home.noTranscript')
})
const aiEstimateHint = computed(() => {
  if (!aiTaskInProgress.value) return ''
  return t('home.aiEstimate')
})
const visibleTranscriptSegments = computed(() => {
  const segments = transcriptSegments.value
  return transcriptExpanded.value ? segments : segments.slice(0, 10)
})
const transcriptText = computed(() =>
  transcriptSegments.value
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

const getRealAiProgress = () => {
  if (aiTask.value?.status === 'completed' || aiTask.value?.status === 'no_transcript') {
    return 100
  }
  return Math.min(100, Math.max(0, Number(aiTask.value?.progress || 0)))
}

const getSmoothAiProgressCeiling = () => {
  const real = getRealAiProgress()
  const status = aiTask.value?.status
  if (status === 'extracting') {
    if (real >= 38) return 67
    if (real >= 18) return 37
    return 24
  }
  if (status === 'summarizing') {
    if (real >= 68) return 87
    return 76
  }
  if (status === 'queued') return 18
  return real
}

const getEstimatedAsrSeconds = () => {
  const duration = Number(info.value?.duration || 0)
  if (!duration) return 240
  if (duration <= 180) return 90
  if (duration <= 600) return Math.round(duration * 0.75)
  if (duration <= 1800) return Math.round(duration * 0.62)
  if (duration <= 3600) return Math.round(duration * 0.5)
  return Math.round(duration * 0.42)
}

const getAiProgressStep = () => {
  const real = getRealAiProgress()
  const status = aiTask.value?.status
  if (status === 'extracting' && real >= 38) {
    const estimatedSeconds = getEstimatedAsrSeconds()
    const availablePoints = Math.max(1, getSmoothAiProgressCeiling() - displayAiProgress.value)
    const intervalSeconds = 2.2
    return Math.max(0.12, Math.min(1.2, (availablePoints * intervalSeconds) / estimatedSeconds))
  }
  if (status === 'summarizing') {
    return 0.6
  }
  return 0.8
}

const syncDisplayAiProgress = () => {
  const real = getRealAiProgress()
  if (real >= displayAiProgress.value || !aiTaskInProgress.value) {
    displayAiProgress.value = real
  }
}

const stopAiProgressSmoothing = () => {
  if (aiProgressTimer.value) {
    window.clearInterval(aiProgressTimer.value)
    aiProgressTimer.value = null
  }
}

const startAiProgressSmoothing = () => {
  stopAiProgressSmoothing()
  syncDisplayAiProgress()
  aiProgressTimer.value = window.setInterval(() => {
    if (!aiTaskInProgress.value) {
      syncDisplayAiProgress()
      stopAiProgressSmoothing()
      return
    }
    const real = getRealAiProgress()
    if (real > displayAiProgress.value) {
      displayAiProgress.value = real
      return
    }
    const ceiling = getSmoothAiProgressCeiling()
    if (displayAiProgress.value < ceiling) {
      displayAiProgress.value = Math.min(ceiling, displayAiProgress.value + getAiProgressStep())
    }
  }, 2200)
}
const aiResultTabs = computed(() => [
  { id: 'summary', label: aiContentLabels.value.summaryTab, icon: '📋' },
  { id: 'transcript', label: aiContentLabels.value.transcriptTab, icon: '📜' },
  { id: 'mindmap', label: aiContentLabels.value.mindmapTab, icon: '🧠' },
  { id: 'chat', label: aiContentLabels.value.chatTab, icon: '💬' },
])
const highlightIcons = ['💡', '🧠', '🚀', '🎯', '✨', '📌']
const getHighlightIcon = (index) => highlightIcons[index % highlightIcons.length]
const aiContentLabels = computed(() => ({
  summaryTab: t('home.ai.summaryTab'),
  transcriptTab: t('home.ai.transcriptTab'),
  mindmapTab: t('home.ai.mindmapTab'),
  chatTab: t('home.ai.chatTab'),
  videoOverview: t('home.ai.videoOverview'),
  contentOutline: t('home.ai.contentOutline'),
  keyPoints: t('home.ai.keyPoints'),
  keywords: t('home.ai.keywords'),
  learningSuggestions: t('home.ai.learningSuggestions'),
  copyMarkdown: t('home.ai.copyMarkdown'),
  downloadMarkdown: t('home.ai.downloadMarkdown'),
  summaryTitleFallback: t('home.ai.summaryTitleFallback'),
  pointFallback: t('home.ai.pointFallback'),
  highlightsHeading: t('home.ai.highlightsHeading'),
  outlineHeading: t('home.ai.outlineHeading'),
  timelineHeading: t('home.ai.timelineHeading'),
}))
const summaryTitle = computed(() => aiTask.value?.summary?.title || info.value?.title || aiTask.value?.title || aiContentLabels.value.summaryTitleFallback)
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
      title: outlinePoint.title || `${aiContentLabels.value.pointFallback} ${index + 1}`,
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
    lines.push(`## ${aiContentLabels.value.highlightsHeading}`)
    summary.key_points.forEach((point) => lines.push(`- ${point}`))
    lines.push('')
  }
  if (summary.outline?.length) {
    lines.push(`## ${aiContentLabels.value.outlineHeading}`)
    summary.outline.forEach((item, index) => lines.push(`${index + 1}. ${item}`))
    lines.push('')
  }
  if (summary.timeline?.length) {
    lines.push(`## ${aiContentLabels.value.timelineHeading}`)
    summary.timeline.forEach((item) => lines.push(`- **${item.time} ${item.title}**：${item.summary}`))
    lines.push('')
  }
  if (summary.keywords?.length) {
    lines.push(`## ${aiContentLabels.value.keywords}`, summary.keywords.map((item) => `\`${item}\``).join(' '), '')
  }
  if (summary.learning_suggestions?.length) {
    lines.push(`## ${aiContentLabels.value.learningSuggestions}`)
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
  return height ? `${height}p` : resolution || t('home.format.original')
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
  const segments = transcriptSegments.value
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
    const lang = aiTask.value?.transcript_language || t('home.ai.transcriptMdUnknown')
    return [
      `# ${title}`,
      '',
      t('home.ai.transcriptMdLang', { lang }),
      '',
      `| ${t('home.ai.transcriptMdTime')} | ${t('home.ai.transcriptMdText')} |`,
      '| --- | --- |',
      ...segments.map((segment) => `| ${formatDuration(segment.start)} | ${String(segment.text || '').replace(/\|/g, '\\|')} |`),
    ].join('\n')
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

const closeFloatingMenus = () => {
  transcriptDownloadOpen.value = false
}

const handleDocumentClick = (event) => {
  if (!event.target?.closest?.('.download-menu')) {
    transcriptDownloadOpen.value = false
  }
}

const handleDocumentKeydown = (event) => {
  if (event.key === 'Escape') {
    closeFloatingMenus()
  }
}

const formatChoices = computed(() => {
  void locale.value
  if (!info.value) {
    return []
  }

  const byResolution = new Map()

  for (const format of info.value.formats || []) {
    if (!format.format_id || !isVideoLikeFormat(format)) {
      continue
    }

    const resolution = format.resolution || t('home.format.original')
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
      const sizeText = size ? `${(size / 1024 / 1024).toFixed(1)}MB` : t('home.format.unknownSize')
      const resolution = getDisplayResolution(format.resolution)
      const ext = format.ext ? format.ext.toUpperCase() : t('home.format.media')
      const typeText = hasVideo && !hasAudio ? t('home.format.videoAudioMerge') : hasVideo && hasAudio ? t('home.format.videoAudio') : t('home.format.videoOnly')
      const height = getResolutionHeight(format.resolution)
      const vipOnly = !userStore.isVip && height > 720

      return {
        id: getFormatDownloadValue(format),
        title: `${resolution} ${ext} (${typeText}${size ? `, ${sizeText}` : ''})`,
        meta: `${format.ext || 'media'} · ${hasAudio ? t('home.format.withAudio') : t('home.format.mergeAudio')}`,
        resolution,
        size: size || 0,
        hasAudio,
        hasVideo,
        height,
        vipOnly,
      }
    })
    .sort((a, b) => {
      return b.height - a.height || b.size - a.size
    })
    .map((format, index) => ({
      ...format,
      title:
        index === 0
          ? t('home.format.best', {
              resolution: format.resolution,
              type: format.hasAudio ? t('home.format.videoAudio') : t('home.format.videoAudioMerge'),
              size: format.size ? `, ${(format.size / 1024 / 1024).toFixed(1)}MB` : '',
            })
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
  downloadedTaskIds.value = new Set()
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
  stopAiProgressSmoothing()
  displayAiProgress.value = 0
}

const clearUrl = () => {
  url.value = ''
  showBiliAuthPanel.value = false
  pendingParseAfterLogin.value = false
  showYouTubeAuthPanel.value = false
  pendingParseAfterYouTubeAuth.value = false
  youtubeCookieAdvancedOpen.value = false
  youtubeCookiesDraft.value = ''
  youtubeAuthMessage.value = ''
  cookiesText.value = ''
  urlInput.value?.focus()
}

const isBiliUrl = (value) => /(^|\.)bilibili\.com|(^|\.)b23\.tv/i.test(String(value || ''))

const isYouTubeUrl = (value) =>
  /(^|\.)youtube\.com|(^|\.)youtube-nocookie\.com|youtu\.be/i.test(String(value || ''))

// 后端在解析失败时可能返回带"412 / 风控挑战 / 扫码登录"等关键词的中文长文案
// （见 backend/app/api/video.py 里的 _humanize_extract_error）。
// 前端检测到这类错误就把它"吞掉"，转成"重新弹码登录"的 UX，不让用户看到那段长说明。
const looksLikeBiliAuthError = (message) =>
  /412|precondition failed|风控|扫码登录|登录态/i.test(String(message || ''))

// YouTube 机房 IP 常触发 bot / sign-in / cookies 类错误；吞掉英文长报错，改弹 Cookie 引导面板。
// 旧版后端在 info 阶段可能误报「清晰度不可用」；解析阶段不应出现该文案。
const looksLikeMisleadingYouTubeClarityError = (message) =>
  /当前清晰度不可用|清晰度不可用|resolution is unavailable/i.test(String(message || ''))

const looksLikeYouTubeServerBlockedError = (message) => {
  const text = String(message || '')
  return (
    /仍然拒绝.*服务器解析|对服务器请求有额外验证|即使提供 cookies/i.test(text) ||
    /still blocked the server|extra verification to server|even with cookies\.txt/i.test(text) ||
    looksLikeMisleadingYouTubeClarityError(text)
  )
}

const resolveYouTubeInfoError = (message) => {
  if (looksLikeYouTubeServerBlockedError(message) || looksLikeMisleadingYouTubeClarityError(message)) {
    return t('home.youtubeInfoParseFailed')
  }
  return message
}

const looksLikeYouTubeAuthError = (message) => {
  const text = String(message || '')
  const lower = text.toLowerCase()
  return (
    /sign in to confirm/i.test(text) ||
    /not a bot/i.test(text) ||
    /bot verification/i.test(lower) ||
    /confirm you.?re not a robot/i.test(lower) ||
    /cookies-from-browser/i.test(lower) ||
    /cookies are required/i.test(lower) ||
    /cookies are no longer valid/i.test(lower) ||
    /use --cookies/i.test(lower) ||
    /\b429\b/.test(text) ||
    /too many requests/i.test(lower) ||
    /login required/i.test(lower) ||
    /unable to download webpage/i.test(lower)
  )
}

const resetBiliLoginState = () => {
  biliLoggedIn.value = false
  biliSessionId.value = ''
  biliQrImage.value = ''
  biliLoginMessage.value = ''
  forgetBiliSession()
  if (biliPollTimer.value) {
    window.clearInterval(biliPollTimer.value)
    biliPollTimer.value = null
  }
}

const focusBiliAuthPanel = () => {
  nextTick(() => {
    try {
      biliAuthPanelEl.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } catch {
      /* ignore */
    }
  })
}

const focusYouTubeAuthPanel = () => {
  nextTick(() => {
    try {
      youtubeAuthPanelEl.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } catch {
      /* ignore */
    }
  })
}

const dismissYouTubeAuthPanel = () => {
  showYouTubeAuthPanel.value = false
  pendingParseAfterYouTubeAuth.value = false
  youtubeCookieAdvancedOpen.value = false
  youtubeAuthMessage.value = ''
}

const openYouTubeCookieAdvanced = () => {
  youtubeCookieAdvancedOpen.value = true
  nextTick(() => {
    try {
      const input = youtubeAuthPanelEl.value?.querySelector('.youtube-cookie-input')
      input?.focus()
    } catch {
      /* ignore */
    }
  })
}

const triggerYouTubeCookieUpload = () => {
  youtubeCookieFileInput.value?.click()
}

const onYouTubeCookieFileChange = async (event) => {
  const [file] = Array.from(event.target.files || [])
  if (!file) {
    return
  }
  try {
    youtubeCookiesDraft.value = await file.text()
    youtubeAuthMessage.value = t('home.youtubeCookieFileLoaded', { name: file.name })
  } catch {
    youtubeAuthMessage.value = t('home.youtubeCookieFileFailed')
  }
  event.target.value = ''
}

const submitYouTubeCookiesAndParse = async () => {
  const trimmed = youtubeCookiesDraft.value.trim()
  if (!trimmed) {
    youtubeAuthMessage.value = t('home.youtubeCookieEmpty')
    return
  }
  cookiesText.value = trimmed
  youtubeAuthMessage.value = ''
  pendingParseAfterYouTubeAuth.value = false
  await parseInfo()
}

const triggerFileDownload = (downloadUrl, taskId) => {
  if (!downloadUrl || downloadedTaskIds.value.has(taskId)) {
    return
  }
  downloadedTaskIds.value.add(taskId)
  const link = document.createElement('a')
  // 后端返回 /api/files/<task_id> 是相对路径；浏览器原生 <a> 跳转不会走前端 fetch 包装，
  // 会按当前页面域名解析 → 错落到 Cloudflare Pages（前端域）→ 拿到 SPA index.html。
  // 必须显式拼上后端 API 域名，浏览器才会去 api-videodown.cozyguidehub.com 取真实文件。
  link.href = resolveApiUrl(downloadUrl)
  link.download = ''
  link.rel = 'noreferrer'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const parseInfo = async () => {
  if (!canSubmit.value) {
    return
  }
  const requestUrl = url.value.trim()
  const isBili = isBiliUrl(requestUrl)
  const isYouTube = isYouTubeUrl(requestUrl)

  // 预检：B 站链接 + 还没扫码登录 → 直接弹码，不发起会触发 WAF 412 的 /api/video/info 调用。
  // 扫码成功后由 startBiliLogin 内部 polling 自动回调 parseInfo() 继续解析。
  if (isBili && !activeAuthSessionId.value) {
    showBiliAuthPanel.value = true
    pendingParseAfterLogin.value = true
    error.value = ''
    focusBiliAuthPanel()
    if (!biliLoginLoading.value && !biliPollTimer.value) {
      await startBiliLogin()
    }
    return
  }

  showBiliAuthPanel.value = isBili
  resetResult()
  loading.value = true
  try {
    info.value = await getVideoInfo(
      requestUrl,
      cookiesText.value.trim(),
      useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : '',
      activeAuthSessionId.value,
    )
    const defaultPick = formatChoices.value.find((item) => !item.vipOnly) || formatChoices.value[0]
    selectedFormat.value = defaultPick?.id || ''
    if (isYouTube) {
      showYouTubeAuthPanel.value = false
      pendingParseAfterYouTubeAuth.value = false
      youtubeCookieAdvancedOpen.value = false
    }
  } catch (err) {
    // 兜底：扫过码但 session 过期 / 后端被 WAF 撞 412 / 其他登录态失效场景。
    // 不显示 backend 那段"B 站风控挑战 + 长建议"，直接清空会话 + 重新弹码 + 自动续解析。
    if (isBili && looksLikeBiliAuthError(err?.message)) {
      resetBiliLoginState()
      showBiliAuthPanel.value = true
      pendingParseAfterLogin.value = true
      biliLoginMessage.value = t('home.biliSessionExpiredHint')
      error.value = ''
      focusBiliAuthPanel()
      await startBiliLogin()
      return
    }
    if (isYouTube) {
      const hadCookies = Boolean(cookiesText.value.trim())
      const friendlyMessage = resolveYouTubeInfoError(err?.message)
      if (!hadCookies && looksLikeYouTubeAuthError(err?.message)) {
        showYouTubeAuthPanel.value = true
        pendingParseAfterYouTubeAuth.value = false
        youtubeCookieAdvancedOpen.value = false
        error.value = ''
        if (!youtubeCookiesDraft.value.trim() && cookiesText.value.trim()) {
          youtubeCookiesDraft.value = cookiesText.value.trim()
        }
        focusYouTubeAuthPanel()
        return
      }
      showYouTubeAuthPanel.value = false
      pendingParseAfterYouTubeAuth.value = false
      youtubeCookieAdvancedOpen.value = false
      youtubeAuthMessage.value = ''
      error.value = friendlyMessage
      return
    }
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
      syncDisplayAiProgress()
      if (['completed', 'failed', 'no_transcript'].includes(aiTask.value.status)) {
        window.clearInterval(aiPollingTimer.value)
        aiPollingTimer.value = null
        stopAiProgressSmoothing()
      }
    } catch (err) {
      error.value = err.message
      window.clearInterval(aiPollingTimer.value)
      aiPollingTimer.value = null
    }
  }, 1400)
}

const startAiSummary = async () => {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: '/' } })
    return
  }
  if (!info.value || aiLoading.value || aiTaskInProgress.value) {
    return
  }
  error.value = ''
  aiLoading.value = true
  transcriptExpanded.value = false
  activeAiTab.value = 'summary'
  aiTask.value = null
  displayAiProgress.value = 0
  try {
    const created = await createAiSummaryTask({
      url: url.value.trim(),
      cookies: cookiesText.value.trim() || null,
      browser_cookies: useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : null,
      auth_session_id: activeAuthSessionId.value || null,
    })
    aiTask.value = created
    syncDisplayAiProgress()
    startAiProgressSmoothing()
    pollAiSummaryTask(created.task_id)
  } catch (err) {
    error.value = err.message
  } finally {
    aiLoading.value = false
  }
}

const handleSubtitleSummaryCreated = (created) => {
  aiTask.value = created
  displayAiProgress.value = Number(created.progress || 0)
  startAiProgressSmoothing()
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
    error.value = t('home.copyFailedTranscript')
  }
}

const copySummaryMarkdown = async () => {
  if (!summaryMarkdown.value) {
    return
  }
  try {
    await window.navigator.clipboard.writeText(summaryMarkdown.value)
  } catch {
    error.value = t('home.copyFailedSummary')
  }
}

const downloadSummaryMarkdown = () => {
  if (!summaryMarkdown.value) {
    return
  }
  downloadTextFile(summaryMarkdown.value, `${getSafeFilename(summaryTitle.value)}-总结.md`, 'text/markdown;charset=utf-8')
}

const stopBatchPollers = () => {
  for (const timer of batchPollTimers.value) {
    window.clearInterval(timer)
  }
  batchPollTimers.value = []
}

const batchStatusText = (status) => {
  const key = `home.taskStatus.${status}`
  return t(key) !== key ? t(key) : status
}

const pollBatchTask = (row) => {
  if (!row?.task_id) return
  const timer = window.setInterval(async () => {
    try {
      const status = await getTask(row.task_id)
      row.status = status.status
      row.progress = status.progress
      row.liveMessage = status.error || batchStatusText(status.status)
      if (status.status === 'completed') {
        row.liveMessage = t('home.batchDone')
        triggerFileDownload(status.download_url, row.task_id)
        window.clearInterval(timer)
        batchPollTimers.value = batchPollTimers.value.filter((id) => id !== timer)
      } else if (status.status === 'failed') {
        row.error = status.error || t('home.taskStatus.failed')
        row.liveMessage = row.error
        window.clearInterval(timer)
        batchPollTimers.value = batchPollTimers.value.filter((id) => id !== timer)
      }
    } catch (err) {
      row.error = err.message
      row.liveMessage = err.message
      window.clearInterval(timer)
      batchPollTimers.value = batchPollTimers.value.filter((id) => id !== timer)
    }
  }, 1500)
  batchPollTimers.value.push(timer)
}

const submitBatchDownload = async () => {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: '/' } })
    return
  }
  if (!userStore.isVip) {
    error.value = t('home.batchVipOnly')
    router.push('/pricing')
    return
  }
  const urls = batchUrlsText.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (!urls.length) {
    error.value = t('home.batchEmpty')
    return
  }
  stopBatchPollers()
  batchLoading.value = true
  error.value = ''
  batchResults.value = []
  try {
    const data = await createBatchDownload({
      urls,
      format: selectedFormat.value || 'best',
      with_subtitle: false,
      cookies: cookiesText.value.trim() || null,
      browser_cookies: useBrowserCookies.value && !cookiesText.value.trim() ? browserCookies.value : null,
      auth_session_id: activeAuthSessionId.value || null,
    })
    batchResults.value = (data.tasks || []).map((row) => ({
      ...row,
      progress: 0,
      liveMessage: row.error ? row.error : batchStatusText(row.status || 'queued'),
    }))
    const queued = batchResults.value.filter((row) => row.task_id && !row.error)
    if (!queued.length && batchResults.value.some((row) => row.error)) {
      error.value = t('home.batchAllFailed')
    } else if (queued.length) {
      error.value = ''
      for (const row of queued) {
        pollBatchTask(row)
      }
    }
  } catch (err) {
    error.value = err.message
  } finally {
    batchLoading.value = false
  }
}

const downloadSelected = async () => {
  if (!canDownload.value) {
    return
  }
  const picked = formatChoices.value.find((item) => item.id === selectedFormat.value)
  if (picked?.vipOnly) {
    error.value = t('home.format.vipResolution', { resolution: picked.resolution })
    router.push('/pricing')
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

const openAiTaskFromQuery = async (taskId) => {
  if (!taskId) return
  aiLoading.value = true
  error.value = ''
  try {
    aiTask.value = await getAiSummaryTask(taskId)
    if (aiTask.value.status === 'completed' || aiTask.value.status === 'no_transcript') {
      activeAiTab.value = 'summary'
      return
    }
    pollAiSummaryTask(taskId)
  } catch (err) {
    error.value = err.message
  } finally {
    aiLoading.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
  const aiTaskId = typeof route.query.ai_task === 'string' ? route.query.ai_task : ''
  if (aiTaskId) {
    await openAiTaskFromQuery(aiTaskId)
  }
  if (urlInput.value && !url.value) {
    const autofilled = urlInput.value.value?.trim()
    if (autofilled) url.value = autofilled
  }
  const storedSessionId = window.localStorage.getItem(BILI_AUTH_STORAGE_KEY)
  if (!storedSessionId) {
    return
  }
  try {
    const status = await getBiliQrStatus(storedSessionId)
    if (status.is_logged_in) {
      biliSessionId.value = storedSessionId
      biliLoggedIn.value = true
      biliLoginMessage.value = t('home.biliRestored')
      return
    }
    forgetBiliSession()
  } catch {
    forgetBiliSession()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
  }
  if (biliPollTimer.value) {
    window.clearInterval(biliPollTimer.value)
  }
  if (aiPollingTimer.value) {
    window.clearInterval(aiPollingTimer.value)
  }
  stopBatchPollers()
  stopAiProgressSmoothing()
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
    biliLoginMessage.value = t('home.biliScanHint')
    biliPollTimer.value = window.setInterval(async () => {
      try {
        const status = await getBiliQrStatus(result.session_id)
        biliLoginMessage.value = status.message
        biliLoggedIn.value = status.is_logged_in
        if (status.is_logged_in) {
          rememberBiliSession(result.session_id)
          window.clearInterval(biliPollTimer.value)
          biliPollTimer.value = null
          // 如果用户当时是因为粘贴 B 站链接被拦下来才弹码的，
          // 登录成功后自动续上"解析视频"动作，避免让用户再点一次按钮。
          if (pendingParseAfterLogin.value && url.value.trim()) {
            pendingParseAfterLogin.value = false
            // 给"登录成功"提示一个短暂展示时间，再隐藏面板继续解析。
            setTimeout(() => {
              showBiliAuthPanel.value = false
              parseInfo()
            }, 600)
          }
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
  <section id="console" :class="['hero', { 'has-result': info, compact: heroCompact }]">
    <span v-if="!heroCompact" class="support-pill">
      <span></span>
      {{ t('home.supportPill') }}
    </span>

    <div v-if="!heroCompact" class="hero-copy">
      <h1>{{ t('home.heroTitle') }}<em>{{ t('home.heroTitleEm') }}</em></h1>
      <p class="subtitle">{{ t('home.heroSubtitle') }}</p>
    </div>

    <section class="search-card" :aria-label="t('home.searchAria')">
      <div class="search-bar">
        <label class="sr-only" for="video-url">{{ t('home.urlLabel') }}</label>
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
          :placeholder="t('home.urlPlaceholder')"
          @keyup.enter="parseInfo"
        />
        <button
          v-if="url"
          class="clear-url-button"
          type="button"
          :aria-label="t('home.clearUrlAria')"
          :title="t('home.clearUrlTitle')"
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
          <template v-if="taskInProgress">{{ downloadProgress }}%</template>
          <template v-else-if="loading"><span class="spin-loader" aria-hidden="true"></span></template>
          <template v-else>{{ t('home.parseVideo') }}</template>
        </button>
      </div>

      <div v-if="userStore.isLoggedIn" class="batch-row">
        <button type="button" class="batch-toggle" @click="batchOpen = !batchOpen">
          {{ batchOpen ? t('home.batchHide') : t('home.batchShow') }}
        </button>
        <div v-if="batchOpen" class="batch-panel">
          <p class="batch-hint">{{ userStore.isVip ? t('home.batchHintVip') : t('home.batchHintFree') }}</p>
          <textarea
            v-model="batchUrlsText"
            class="batch-textarea"
            rows="4"
            :placeholder="t('home.batchPlaceholder')"
          ></textarea>
          <div
            v-if="batchInProgress"
            class="batch-progress"
            role="progressbar"
            :aria-valuenow="batchProgressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="t('home.batchProgressAria', { percent: batchProgressPercent })"
          >
            <div class="batch-progress-fill" :style="{ width: `${batchProgressPercent}%` }"></div>
            <span class="batch-progress-text">{{ batchProgressPercent }}%</span>
          </div>
          <button
            v-else
            type="button"
            class="batch-submit"
            :disabled="!batchUrlsText.trim()"
            @click="submitBatchDownload"
          >
            {{ t('home.batchSubmit') }}
          </button>
          <ul v-if="batchResults.length" class="batch-results">
            <li v-for="(row, idx) in batchResults" :key="idx">
              <span class="batch-url">{{ row.url }}</span>
              <span :class="row.error ? 'batch-fail' : 'batch-ok'">
                {{ row.liveMessage || row.error || row.status }}
              </span>
            </li>
          </ul>
        </div>
      </div>

      <div v-if="!heroCompact" class="quick-row">
        <span>{{ t('home.tryLabel') }}</span>
        <button type="button">YouTube</button>
        <button type="button">Bilibili</button>
        <button type="button">Twitter/X</button>
      </div>

      <div v-if="showBiliAuthPanel" ref="biliAuthPanelEl" class="bili-auth-panel">
        <div v-if="!biliLoggedIn" class="bili-auth-prompt">
          <h3>{{ t('home.biliAutoPromptTitle') }}</h3>
          <p>{{ t('home.biliAutoPromptSubtitle') }}</p>
        </div>
        <button class="bili-auth-trigger" type="button" :disabled="biliLoginLoading" @click="startBiliLogin">
          {{
            biliLoginLoading
              ? t('home.biliGeneratingQr')
              : biliLoggedIn
                ? t('home.biliLoggedIn')
                : biliQrImage
                  ? t('home.biliRegenerateQr')
                  : t('home.biliLoginCta')
          }}
        </button>
        <div v-if="biliQrImage || biliLoginMessage" class="bili-login-box">
          <img v-if="biliQrImage && !biliLoggedIn" class="bili-qr" :src="biliQrImage" :alt="t('home.biliQrAlt')" />
          <span v-if="biliLoginMessage" :class="['bili-login-message', { success: biliLoggedIn }]">
            {{ biliLoginMessage }}
          </span>
        </div>
      </div>

      <div v-if="showYouTubeAuthPanel" ref="youtubeAuthPanelEl" class="youtube-auth-panel">
        <div class="youtube-auth-prompt">
          <h3>{{ t('home.youtubeAuthTitle') }}</h3>
          <p>{{ t('home.youtubeAuthSubtitle') }}</p>
          <p class="youtube-auth-hint">{{ t('home.youtubeAuthDisclaimer') }}</p>
        </div>

        <div v-if="!youtubeCookieAdvancedOpen" class="youtube-auth-simple">
          <div class="youtube-auth-actions">
            <RouterLink
              class="youtube-auth-button link"
              :to="{ name: 'help-youtube-cookies' }"
            >
              {{ t('home.youtubeAuthViewGuide') }}
            </RouterLink>
            <button class="youtube-auth-button" type="button" @click="openYouTubeCookieAdvanced">
              {{ t('home.youtubeAuthHaveCookies') }}
            </button>
            <button class="youtube-auth-button muted" type="button" @click="dismissYouTubeAuthPanel">
              {{ t('home.youtubeAuthTryLater') }}
            </button>
          </div>
        </div>

        <div v-else class="youtube-auth-advanced">
          <p class="youtube-auth-hint">{{ t('home.youtubeAuthAdvancedHint') }}</p>
          <textarea
            v-model="youtubeCookiesDraft"
            class="youtube-cookie-input"
            rows="5"
            :placeholder="t('home.youtubeCookiePlaceholder')"
            spellcheck="false"
            autocomplete="off"
          ></textarea>
          <input
            ref="youtubeCookieFileInput"
            class="youtube-auth-file"
            type="file"
            accept=".txt,text/plain"
            @change="onYouTubeCookieFileChange"
          />
          <div class="youtube-auth-actions">
            <button class="youtube-auth-button" type="button" @click="triggerYouTubeCookieUpload">
              {{ t('home.youtubeCookieUpload') }}
            </button>
            <button
              class="youtube-auth-button primary"
              type="button"
              :disabled="loading"
              @click="submitYouTubeCookiesAndParse"
            >
              {{ loading ? '…' : t('home.youtubeCookieContinue') }}
            </button>
            <button
              class="youtube-auth-button muted"
              type="button"
              :disabled="loading"
              @click="dismissYouTubeAuthPanel"
            >
              {{ t('home.youtubeCookieCancel') }}
            </button>
          </div>
          <p v-if="youtubeAuthMessage" class="youtube-auth-message">{{ youtubeAuthMessage }}</p>
        </div>
      </div>
    </section>
  </section>

  <p v-if="error" class="alert" role="alert">{{ error }}</p>

  <section v-if="info" class="result-panel" :aria-label="t('home.resultAria')">
    <div class="download-card">
      <article class="video-summary">
        <div class="cover-wrap">
          <img
            v-if="coverImageUrl && !coverLoadFailed"
            :src="coverImageUrl"
            :alt="t('home.coverAlt')"
            @error="coverLoadFailed = true"
          />
          <div v-else class="thumbnail-empty"></div>
          <span v-if="info.duration" class="duration-badge">{{ formatDuration(info.duration) }}</span>
        </div>
        <div class="summary-copy">
          <h2>{{ info.title || t('home.untitledVideo') }}</h2>
          <p class="meta-line">
            {{ info.uploader || t('home.unknownUploader') }}
            <span class="source-chip">{{ info.extractor || 'Unknown' }}</span>
            <span v-if="info.duration">{{ t('home.durationPrefix') }} {{ formatDuration(info.duration) }}</span>
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
          {{ t('home.selectFormat') }}
        </h3>
        <div class="format-grid">
          <button
            v-for="format in formatChoices"
            :key="format.id + format.title"
            :class="{ active: selectedFormat === format.id, 'vip-only': format.vipOnly }"
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
              <strong>
                {{ format.title }}
                <span v-if="format.vipOnly" class="vip-tag">{{ t('home.vipTag') }}</span>
              </strong>
              <small>{{ format.meta }}</small>
            </span>
          </button>
        </div>
      </div>

      <div class="download-footer">
        <button class="download-button" :class="{ 'is-loading': downloading || taskInProgress }" :disabled="!canDownload" type="button" @click="downloadSelected">
          <span v-if="downloading || taskInProgress" class="button-loading-dots" aria-hidden="true">
            <i></i>
            <i></i>
            <i></i>
          </span>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 4v10" />
            <path d="m7 10 5 5 5-5" />
            <path d="M5 20h14" />
          </svg>
          {{ downloading || taskInProgress ? `${downloadProgress}%` : t('home.downloadNow') }}
        </button>
        <button class="ai-summary-button" :class="{ 'is-loading': aiTaskInProgress }" :disabled="aiLoading || aiTaskInProgress" type="button" @click="startAiSummary">
          <span v-if="aiTaskInProgress" class="button-loading-dots blue" aria-hidden="true">
            <i></i>
            <i></i>
            <i></i>
          </span>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 3v4" />
            <path d="M12 17v4" />
            <path d="M3 12h4" />
            <path d="M17 12h4" />
            <path d="m6.5 6.5 2.8 2.8" />
            <path d="m14.7 14.7 2.8 2.8" />
            <path d="m17.5 6.5-2.8 2.8" />
            <path d="m9.3 14.7-2.8 2.8" />
          </svg>
          {{
            aiTaskInProgress
              ? `${aiProgress}%`
              : aiTask?.status === 'completed'
                ? t('home.aiResummary')
                : t('home.aiSummary')
          }}
        </button>
        <span class="selected-hint">
          {{
            selectedFormat
              ? t('home.selectedFormat', {
                  title: formatChoices.find((item) => item.id === selectedFormat)?.title,
                })
              : t('home.noFormat')
          }}
        </span>
      </div>
      <p class="download-legal-hint">
        {{ t('home.downloadLegalHint') }}
        <RouterLink to="/legal/copyright">{{ t('home.downloadLegalLink') }}</RouterLink>
      </p>

      <p v-if="aiEstimateHint" class="ai-estimate-hint">
        <span class="text-loading-dots" aria-hidden="true">
          <i></i>
          <i></i>
          <i></i>
        </span>
        <span>{{ aiEstimateHint }}<span class="loading-ellipsis"></span></span>
      </p>
      <p v-if="task?.status === 'failed'" class="download-error">{{ task.error }}</p>
      <p v-else-if="task?.download_url" class="download-success">{{ t('home.downloadDone') }}</p>
    </div>

    <section class="ai-summary-panel" :aria-label="t('home.aiPanelAria')">
      <div v-if="aiTask" :class="['ai-task-state', { warning: aiTask.status === 'no_transcript' }]" aria-live="polite">
        <p v-if="aiTask.status === 'no_transcript'" class="ai-empty-state">
          {{ aiNoTranscriptMessage }}
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
        <div class="ai-tab-list" role="tablist" :aria-label="t('home.aiResultTabs')">
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
                <h2 class="sr-only">{{ summaryTitle }}</h2>
                <div class="ai-doc-actions" :aria-label="t('home.summaryExportAria')">
                  <button class="text-action-button" type="button" @click="copySummaryMarkdown">{{ aiContentLabels.copyMarkdown }}</button>
                  <button class="text-action-button" type="button" @click="downloadSummaryMarkdown">{{ aiContentLabels.downloadMarkdown }}</button>
                </div>
              </header>

              <section class="ai-doc-section ai-doc-overview">
                <h2>{{ aiContentLabels.videoOverview }}</h2>
                <p>{{ aiTask.summary.one_sentence }}</p>
              </section>

              <section v-if="summaryOutlineSections.length" class="ai-doc-section ai-doc-outline">
                <h2>{{ aiContentLabels.contentOutline }}</h2>
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
                <h2>{{ aiContentLabels.keyPoints }}</h2>
                <ul>
                  <li v-for="(point, index) in summaryHighlights" :key="`${point.title}-${index}`">
                    <strong>{{ point.title }}</strong>
                    <template v-if="point.body">：{{ point.body }}</template>
                  </li>
                </ul>
              </section>

              <section v-if="aiTask.summary.keywords?.length" class="ai-doc-section">
                <h2>{{ aiContentLabels.keywords }}</h2>
                <p class="ai-doc-keywords">
                  <span v-for="keyword in aiTask.summary.keywords" :key="keyword">{{ keyword }}</span>
                </p>
              </section>

              <section v-if="aiTask.summary.learning_suggestions?.length" class="ai-doc-section">
                <h2>{{ aiContentLabels.learningSuggestions }}</h2>
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
                <h4>{{ t('home.transcriptTitle') }}</h4>
                <p>
                  {{ t('home.transcriptCount', { count: transcriptSegments.length }) }}
                  <span class="transcript-language">{{ aiTask.transcript_language || t('home.unknownLanguage') }}</span>
                </p>
              </div>
              <div class="transcript-actions" :aria-label="t('home.transcriptActionsAria')">
                <button class="text-action-button" type="button" @click="copyTranscript">{{ t('home.copyTranscript') }}</button>
                <div class="download-menu">
                  <button
                    class="text-action-button download-menu-trigger"
                    type="button"
                    :aria-expanded="transcriptDownloadOpen"
                    aria-haspopup="menu"
                    @click="toggleTranscriptDownload"
                  >
                    {{ t('home.download') }}
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
            <div v-if="transcriptSegments.length" class="transcript-list">
              <p v-for="segment in transcriptSegments" :key="`${segment.start}-${segment.text}`">
                <time>{{ formatDuration(segment.start) }}</time>
                <span>{{ segment.text }}</span>
              </p>
            </div>
            <p v-else class="transcript-empty">{{ t('home.transcriptEmpty') }}</p>
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
      <h2>{{ t('home.features.title') }} <span>{{ t('home.features.titleBrand') }}</span></h2>
      <p>{{ t('home.features.subtitle') }}</p>
    </div>
    <div class="feature-grid">
      <article>
        <span class="feature-icon globe">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8" />
            <path d="M4 12h16M12 4c2 2.4 3 5.1 3 8s-1 5.6-3 8M12 4c-2 2.4-3 5.1-3 8s1 5.6 3 8" />
          </svg>
        </span>
        <h3>{{ t('home.features.platformsTitle') }}</h3>
        <p>{{ t('home.features.platformsDesc') }}</p>
      </article>
      <article>
        <span class="feature-icon lightning">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M13 3 6 13h5l-1 8 8-12h-5l1-6Z" />
          </svg>
        </span>
        <h3>{{ t('home.features.fastTitle') }}</h3>
        <p>{{ t('home.features.fastDesc') }}</p>
      </article>
      <article>
        <span class="feature-icon mobile">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="7" y="3" width="10" height="18" rx="2.5" />
            <path d="M11 17h2" />
          </svg>
        </span>
        <h3>{{ t('home.features.mobileTitle') }}</h3>
        <p>{{ t('home.features.mobileDesc') }}</p>
      </article>
      <article>
        <span class="feature-icon quality">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 5h14v14H5z" />
            <path d="M8 9h8M8 13h5" />
            <path d="m15 14 2 2 3-4" />
          </svg>
        </span>
        <h3>{{ t('home.features.qualityTitle') }}</h3>
        <p>{{ t('home.features.qualityDesc') }}</p>
      </article>
      <article>
        <span class="feature-icon ai">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="6" width="14" height="12" rx="3" />
            <path d="M9 6V4M15 6V4M9 18v2M15 18v2M8.5 11h.01M15.5 11h.01M10 15h4" />
          </svg>
        </span>
        <h3>{{ t('home.features.aiTitle') }}</h3>
        <p>{{ t('home.features.aiDesc') }}</p>
      </article>
    </div>
  </section>

  <section id="pricing" class="pricing-section">
    <div class="section-heading">
      <h2>{{ t('home.pricing.title') }}</h2>
      <p>{{ t('home.pricing.subtitle') }}</p>
    </div>
    <div class="plan-grid">
      <article class="plan-card free-plan">
        <div>
          <h3>{{ t('home.pricing.freeName') }}</h3>
          <p>{{ t('home.pricing.freeDesc') }}</p>
        </div>
        <p class="plan-price"><strong>¥0</strong><span>{{ t('home.pricing.freePriceUnit') }}</span></p>
        <ul>
          <li>{{ t('home.pricing.freeF1') }}</li>
          <li>{{ t('home.pricing.freeF2') }}</li>
          <li>{{ t('home.pricing.freeF3') }}</li>
          <li>{{ t('home.pricing.freeF4') }}</li>
        </ul>
        <button type="button" class="plan-button muted">{{ t('home.pricing.freeCta') }}</button>
      </article>

      <article class="plan-card vip-plan">
        <span class="recommend-badge">{{ t('home.pricing.vipBadge') }}</span>
        <div>
          <h3>{{ t('home.pricing.vipName') }}</h3>
          <p>{{ t('home.pricing.vipDesc') }}</p>
        </div>
        <p class="plan-price"><strong>¥19</strong><span>{{ t('home.pricing.vipPriceUnit') }}</span><em>{{ t('home.pricing.vipPriceNote') }}</em></p>
        <ul>
          <li>{{ t('home.pricing.vipF1') }}</li>
          <li>{{ t('home.pricing.vipF2') }}</li>
          <li>{{ t('home.pricing.vipF3') }}</li>
          <li>{{ t('home.pricing.vipF4') }}</li>
          <li>{{ t('home.pricing.vipF5') }}</li>
        </ul>
        <RouterLink to="/pricing" class="plan-button primary">{{ t('home.pricing.vipCta') }}</RouterLink>
      </article>
    </div>
  </section>

  <section class="faq-section" aria-labelledby="faq-title">
    <div class="section-heading">
      <h2 id="faq-title">{{ t('home.faq.title') }}</h2>
      <p>{{ t('home.faq.subtitle') }}</p>
    </div>
    <div class="faq-grid">
      <article>
        <h3>{{ t('home.faq.q1') }}</h3>
        <p>{{ t('home.faq.a1') }}</p>
      </article>
      <article>
        <h3>{{ t('home.faq.q2') }}</h3>
        <p>{{ t('home.faq.a2') }}</p>
      </article>
      <article>
        <h3>{{ t('home.faq.q3') }}</h3>
        <p>{{ t('home.faq.a3') }}</p>
      </article>
      <article>
        <h3>{{ t('home.faq.q4') }}</h3>
        <p>{{ t('home.faq.a4') }}</p>
      </article>
    </div>
  </section>
</template>
