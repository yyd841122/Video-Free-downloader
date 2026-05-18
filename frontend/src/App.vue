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
const aiResultTabs = computed(() => [
  { id: 'summary', label: '总结摘要', icon: '📋' },
  { id: 'transcript', label: '字幕文本', icon: '📜' },
  { id: 'mindmap', label: '思维导图', icon: '🧠' },
  { id: 'chat', label: 'AI 问答', icon: '💬' },
])
const highlightIcons = ['💡', '🧠', '🚀', '🎯', '✨', '📌']
const getHighlightIcon = (index) => highlightIcons[index % highlightIcons.length]

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
  urlInput.value?.focus()
}

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
  resetResult()
  loading.value = true
  try {
    info.value = await getVideoInfo(
      url.value.trim(),
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
      <section id="console" class="hero">
        <span class="support-pill">
          <span></span>
          支持 1800+ 平台，永久免费使用
        </span>

        <div class="hero-copy">
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

          <div class="quick-row">
            <span>试试：</span>
            <button type="button">YouTube</button>
            <button type="button">Bilibili</button>
            <button type="button">Twitter/X</button>
          </div>

          <p class="fine-print">解析完成后选择清晰度和格式，点击立即下载即可。系统会自动选择更稳定的下载方式。</p>
          <div class="bili-auth-panel">
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
            <p class="description-line">
              已解析出可下载清晰度。选择想要的格式，然后点击立即下载。
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
                  <section class="ai-doc-section">
                    <h2>总结</h2>
                    <p>{{ aiTask.summary.one_sentence }}</p>
                  </section>

                  <section class="ai-doc-section">
                    <h2>亮点</h2>
                    <ul class="ai-doc-highlights">
                      <li v-for="(point, index) in aiTask.summary.key_points" :key="point">
                        <span class="ai-doc-emoji" aria-hidden="true">{{ getHighlightIcon(index) }}</span>
                        <strong>{{ point.split('：')[0] }}</strong>
                        <template v-if="point.includes('：')">：{{ point.split('：').slice(1).join('：') }}</template>
                      </li>
                    </ul>
                  </section>

                  <section class="ai-doc-section">
                    <h2>章节总结</h2>
                    <ol class="ai-doc-list">
                      <li v-for="item in aiTask.summary.outline" :key="item">{{ item }}</li>
                    </ol>
                  </section>

                  <section v-if="aiTask.summary.timeline?.length" class="ai-doc-section">
                    <h2>时间轴</h2>
                    <div class="ai-doc-timeline">
                      <p v-for="item in aiTask.summary.timeline" :key="`${item.time}-${item.title}`">
                        <time>{{ item.time }}</time>
                        <strong>{{ item.title }}</strong>
                        <span>{{ item.summary }}</span>
                      </p>
                    </div>
                  </section>

                  <section v-if="aiTask.summary.keywords?.length" class="ai-doc-section">
                    <h2>关键词</h2>
                    <p class="ai-doc-keywords">{{ aiTask.summary.keywords.join('、') }}</p>
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
                    <h4>字幕 / 转录</h4>
                    <p>{{ aiTask.transcript_segments.length }} 条字幕片段，语言：{{ aiTask.transcript_language || '未知' }}</p>
                  </div>
                  <button class="text-action-button" type="button" @click="copyTranscript">复制全文</button>
                </div>
                <div class="transcript-list">
                  <p v-for="segment in visibleTranscriptSegments" :key="`${segment.start}-${segment.text}`">
                    <time>{{ formatDuration(segment.start) }}</time>
                    <span>{{ segment.text }}</span>
                  </p>
                </div>
                <button
                  v-if="aiTask.transcript_segments.length > 10"
                  class="text-action-button"
                  type="button"
                  @click="transcriptExpanded = !transcriptExpanded"
                >
                  {{ transcriptExpanded ? '收起字幕' : `展开全部 ${aiTask.transcript_segments.length} 条` }}
                </button>
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
        <div class="section-heading">
          <h2>为什么选择 <span>SaveAny</span></h2>
          <p>简单、快速、强大的视频下载体验</p>
        </div>
        <div class="feature-grid">
          <article>
            <span>01</span>
            <h3>智能解析链接</h3>
            <p>粘贴视频地址即可识别标题、封面、作者和可下载格式。</p>
          </article>
          <article>
            <span>02</span>
            <h3>多清晰度选择</h3>
            <p>解析完成后直接选择想要的清晰度和格式，清楚不绕弯。</p>
          </article>
          <article>
            <span>03</span>
            <h3>一键保存本地</h3>
            <p>选好格式后点击立即下载，系统自动处理更稳定的保存流程。</p>
          </article>
        </div>
      </section>

      <section id="pricing" class="pricing-band">
        <div>
          <h2>开通 VIP，解锁更高效率</h2>
          <p>后续可扩展批量队列、任务历史、AI 总结、字幕翻译和更长文件保留时长。</p>
        </div>
        <button class="vip-cta" type="button">查看套餐</button>
      </section>

      <section id="platforms" class="platform-band">
        <span>YouTube</span>
        <span>Bilibili</span>
        <span>TikTok</span>
        <span>抖音</span>
        <span>Twitter/X</span>
        <span>更多平台</span>
      </section>

      <section id="safety" class="safety-band">
        <div>
          <h2>尊重版权，也尊重平台规则</h2>
        </div>
        <p>
          本工具默认不绕过 DRM、付费限制或登录权限。使用前请确认你拥有下载和保存内容的权利，并注意第三方平台的账号风控风险。
        </p>
      </section>
    </main>
  </div>
</template>
