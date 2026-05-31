<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { fetchOrders, fetchQuota, fetchTaskHistory, resolveApiUrl, resumeCheckout } from '../api/client'
import { AI_SUMMARY_MVP_ENABLED } from '../constants/mvp'
import { useUserStore } from '../stores/user'

const { t } = useI18n()
const userStore = useUserStore()
const router = useRouter()

const orders = ref([])
const history = ref([])
const quota = ref(null)
const loading = ref(true)
const historyLoading = ref(true)
const error = ref('')
const historyError = ref('')
const resumeLoading = ref('')

const statusLabel = computed(() => ({
  pending: t('account.statusPending'),
  paid: t('account.statusPaid'),
  canceled: t('account.statusCanceled'),
  expired: t('account.statusExpired'),
  refunded: t('account.statusRefunded'),
}))

const vipExpireText = computed(() => {
  if (!userStore.user) return ''
  if (userStore.user.is_lifetime_vip) return t('account.lifetimeVip')
  if (userStore.user.is_vip) {
    const ts = userStore.user.vip_expire_at
    if (!ts) return t('account.vip')
    const d = new Date(ts * 1000)
    const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return t('account.vipUntil', { date })
  }
  return t('account.freeUser')
})

const formatTime = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const chatLimitText = computed(() => {
  if (!AI_SUMMARY_MVP_ENABLED) return t('account.quotaAiBeta')
  if (!quota.value) return '-'
  const n = quota.value.ai_chat_per_task
  if (!n) return t('account.chatUnlimited')
  return t('account.chatPerTask', { n })
})

const aiQuotaText = computed(() => {
  if (!AI_SUMMARY_MVP_ENABLED) return t('account.quotaAiBeta')
  if (!quota.value) return '-'
  return `${quota.value.ai_used_today} / ${quota.value.ai_daily_limit}`
})

const resolutionText = computed(() => {
  if (!quota.value) return '-'
  if (!quota.value.max_resolution) return t('account.resolutionUnlimited')
  return t('account.resolutionMax', { p: quota.value.max_resolution })
})

const loadQuota = async () => {
  try {
    quota.value = await fetchQuota()
  } catch {
    quota.value = null
  }
}

const historyStatusLabel = computed(() => ({
  queued: t('account.historyQueued'),
  starting: t('account.historyRunning'),
  downloading: t('account.historyRunning'),
  processing: t('account.historyRunning'),
  extracting: t('account.historyRunning'),
  summarizing: t('account.historyRunning'),
  completed: t('account.historyCompleted'),
  failed: t('account.historyFailed'),
  no_transcript: t('account.historyFailed'),
}))

const kindLabel = (kind) => (kind === 'ai_summary' ? t('account.historyKindAi') : t('account.historyKindDownload'))

const loadHistory = async () => {
  historyLoading.value = true
  historyError.value = ''
  try {
    const data = await fetchTaskHistory()
    history.value = data.items || []
  } catch (err) {
    historyError.value = err.message || t('account.historyLoadFailed')
  } finally {
    historyLoading.value = false
  }
}

const openHistoryItem = (item) => {
  if (item.kind === 'ai_summary') {
    if (!AI_SUMMARY_MVP_ENABLED) {
      router.push({ path: '/' })
      return
    }
    router.push({ path: '/', query: { ai_task: item.task_id } })
    return
  }
  if (item.download_url) {
    const link = document.createElement('a')
    // 同 HomeView.vue 的 triggerFileDownload：后端给的是 /api/files/<id> 相对路径，
    // 必须显式 resolveApiUrl 拼上后端域名，否则 <a> 会落到前端域 → Cloudflare SPA 返回 index.html。
    link.href = resolveApiUrl(item.download_url)
    link.download = ''
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    link.remove()
  }
}

const loadOrders = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchOrders()
    orders.value = data.items || []
  } catch (err) {
    error.value = err.message || t('account.ordersLoadFailed')
  } finally {
    loading.value = false
  }
}

const continuePay = async (order) => {
  if (order.is_mock) {
    router.push({ name: 'mock-pay', query: { order_no: order.order_no } })
    return
  }
  if (order.status !== 'pending') {
    return
  }
  resumeLoading.value = order.order_no
  error.value = ''
  try {
    const data = await resumeCheckout(order.order_no)
    window.location.href = data.checkout_url
  } catch (err) {
    error.value = err.message || t('account.resumePayFailed')
  } finally {
    resumeLoading.value = ''
  }
}

const isManualOrder = (order) => String(order?.order_no || '').startsWith('MAN')

const isStripeCheckoutOrder = (order) => !order?.is_mock && !isManualOrder(order)

const hasPaidManualOrder = computed(() =>
  orders.value.some((order) => order.status === 'paid' && isManualOrder(order)),
)

const hasPaidStripeOrder = computed(() =>
  orders.value.some((order) => order.status === 'paid' && isStripeCheckoutOrder(order)),
)

const vipSourceNote = computed(() => {
  if (!userStore.isVip) return ''
  if (hasPaidManualOrder.value && hasPaidStripeOrder.value) return t('account.vipSourceMixed')
  if (hasPaidManualOrder.value) return t('account.vipSourceManual')
  if (hasPaidStripeOrder.value) return t('account.vipSourceStripeTest')
  return ''
})

const historyFailedHint = (item) => {
  if (item.status !== 'failed' && item.status !== 'no_transcript') return ''
  return item.kind === 'ai_summary' ? t('account.historyFailedHintAi') : t('account.historyFailedHintDownload')
}

const handleLogout = () => {
  userStore.logout()
  router.push('/')
}

onMounted(async () => {
  await userStore.refresh()
  await Promise.all([loadQuota(), loadOrders(), loadHistory()])
})
</script>

<template>
  <section class="account-page">
    <header class="account-header">
      <h1>{{ t('account.title') }}</h1>
      <button type="button" class="logout" @click="handleLogout">{{ t('account.logout') }}</button>
    </header>

    <div class="profile-card">
      <div class="avatar">{{ (userStore.user?.nickname || userStore.user?.email || '?')[0].toUpperCase() }}</div>
      <div class="info">
        <p class="name">{{ userStore.user?.nickname || userStore.user?.email?.split('@')[0] }}</p>
        <p class="email">{{ userStore.user?.email }}</p>
        <p :class="['vip-line', userStore.isVip ? 'is-vip' : '']">{{ vipExpireText }}</p>
        <p v-if="vipSourceNote" class="vip-source-note">{{ vipSourceNote }}</p>
      </div>
      <div class="profile-actions">
        <RouterLink to="/pricing" class="upgrade-btn">
          {{ userStore.isVip ? t('account.renewOrUpgrade') : t('account.upgrade') }}
        </RouterLink>
      </div>
    </div>

    <section v-if="userStore.isVip" class="membership-notes">
      <p class="benefits-boundary">{{ t('account.vipBenefitsBoundary') }}</p>
    </section>

    <section v-if="quota" class="quota-section">
      <header class="section-head">
        <h2>{{ t('account.myQuota') }}</h2>
        <button type="button" class="refresh" @click="loadQuota">{{ t('account.refresh') }}</button>
      </header>
      <div class="quota-grid">
        <div class="quota-item">
          <span class="label">{{ t('account.quotaAiToday') }}</span>
          <span class="value">{{ aiQuotaText }}</span>
        </div>
        <div class="quota-item">
          <span class="label">{{ t('account.quotaConcurrent') }}</span>
          <span class="value">
            {{ t('account.quotaActive', { download: quota.active_download_tasks, ai: quota.active_ai_tasks }) }}
            · {{ t('account.quotaMaxConcurrent', { n: quota.max_concurrent }) }}
          </span>
        </div>
        <div class="quota-item">
          <span class="label">{{ t('account.quotaResolution') }}</span>
          <span class="value">{{ resolutionText }}</span>
        </div>
        <div class="quota-item">
          <span class="label">{{ t('account.quotaChat') }}</span>
          <span class="value">{{ chatLimitText }}</span>
        </div>
      </div>
    </section>

    <section class="history-section">
      <header class="section-head">
        <h2>{{ t('account.myHistory') }}</h2>
        <button type="button" class="refresh" @click="loadHistory">{{ t('account.refresh') }}</button>
      </header>
      <p v-if="historyError" class="error">{{ historyError }}</p>
      <div v-if="historyLoading" class="muted">{{ t('account.historyLoading') }}</div>
      <div v-else-if="!history.length" class="empty">
        <p>{{ t('account.noHistory') }}</p>
      </div>
      <table v-else class="orders-table history-table">
        <thead>
          <tr>
            <th>{{ t('account.colHistoryType') }}</th>
            <th>{{ t('account.colHistoryTitle') }}</th>
            <th>{{ t('account.colHistoryStatus') }}</th>
            <th>{{ t('account.colCreated') }}</th>
            <th>{{ t('account.colAction') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in history" :key="`${item.kind}-${item.task_id}`">
            <td>{{ kindLabel(item.kind) }}</td>
            <td class="history-title">{{ item.title || item.url }}</td>
            <td class="history-status-cell">
              <span :class="`status status-${item.status === 'completed' ? 'paid' : item.status === 'failed' ? 'canceled' : 'pending'}`">
                {{ historyStatusLabel[item.status] || item.status }}
              </span>
              <p v-if="historyFailedHint(item)" class="history-failed-hint">{{ historyFailedHint(item) }}</p>
            </td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td>
              <button
                v-if="item.kind === 'download' && item.file_available && item.status === 'completed'"
                type="button"
                class="link-btn"
                @click="openHistoryItem(item)"
              >
                {{ t('account.historyRedownload') }}
              </button>
              <button
                v-else-if="
                  AI_SUMMARY_MVP_ENABLED &&
                  item.kind === 'ai_summary' &&
                  item.file_available &&
                  item.status === 'completed'
                "
                type="button"
                class="link-btn"
                @click="openHistoryItem(item)"
              >
                {{ t('account.historyViewAi') }}
              </button>
              <span
                v-else-if="!AI_SUMMARY_MVP_ENABLED && item.kind === 'ai_summary'"
                class="muted-inline"
              >
                {{ t('account.historyAiBeta') }}
              </span>
              <span v-else class="muted-inline">{{ t('account.historyUnavailable') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="orders-section">
      <header class="section-head">
        <h2>{{ t('account.myOrders') }}</h2>
        <button type="button" class="refresh" @click="loadOrders">{{ t('account.refresh') }}</button>
      </header>
      <p class="orders-help">{{ t('account.ordersHelp') }}</p>
      <p class="orders-help orders-help-secondary">{{ t('account.manualOrderExplanation') }}</p>
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="loading" class="muted">{{ t('account.ordersLoading') }}</div>
      <div v-else-if="!orders.length" class="empty">
        <p>{{ t('account.noOrders') }}</p>
        <RouterLink to="/pricing" class="empty-cta">{{ t('account.viewPlans') }}</RouterLink>
      </div>
      <table v-else class="orders-table">
        <thead>
          <tr>
            <th>{{ t('account.colOrderNo') }}</th>
            <th>{{ t('account.colPlan') }}</th>
            <th>{{ t('account.colAmount') }}</th>
            <th>{{ t('account.colStatus') }}</th>
            <th>{{ t('account.colCreated') }}</th>
            <th>{{ t('account.colPaid') }}</th>
            <th>{{ t('account.colAction') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.order_no">
            <td class="mono order-no-cell">
              {{ order.order_no }}
              <span v-if="isManualOrder(order)" class="order-tag manual-tag">{{ t('account.orderManualGrantTag') }}</span>
              <span v-else-if="order.is_mock" class="order-tag mock-tag">{{ t('account.orderDevCheckoutTag') }}</span>
              <span v-else class="order-tag stripe-test-tag">{{ t('account.orderStripeTestTag') }}</span>
              <p v-if="isManualOrder(order) && order.status === 'paid'" class="order-tag-note">
                {{ t('account.orderManualGrantNote') }}
              </p>
            </td>
            <td>{{ order.plan_name }}</td>
            <td class="amount">{{ order.amount_display }}</td>
            <td>
              <span :class="`status status-${order.status}`">{{ statusLabel[order.status] || order.status }}</span>
            </td>
            <td>{{ formatTime(order.created_at) }}</td>
            <td>{{ formatTime(order.paid_at) }}</td>
            <td>
              <button
                v-if="order.status === 'pending'"
                type="button"
                class="link-btn"
                :disabled="resumeLoading === order.order_no"
                @click="continuePay(order)"
              >
                {{
                  resumeLoading === order.order_no
                    ? t('account.resumePayProcessing')
                    : t('account.continuePay')
                }}
              </button>
              <span v-else>{{ t('pricing.dash') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>

<style scoped>
.account-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}
.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.account-header h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
}
.logout {
  padding: 8px 14px;
  font-size: 13px;
  color: #b8332a;
  background: #fff;
  border: 1px solid rgba(184, 51, 42, 0.2);
  border-radius: 999px;
  cursor: pointer;
}
.logout:hover {
  background: #fff1ef;
}
.profile-card {
  display: flex;
  gap: 20px;
  align-items: center;
  padding: 24px 26px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 16px;
  box-shadow: 0 18px 36px rgba(30, 50, 90, 0.04);
}
.avatar {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border-radius: 50%;
}
.info {
  flex: 1;
  min-width: 0;
}
.name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1e2430;
}
.email {
  margin: 4px 0 0;
  font-size: 13px;
  color: #67758a;
}
.vip-line {
  margin: 8px 0 0;
  font-size: 13.5px;
  color: #67758a;
  font-weight: 600;
}
.vip-line.is-vip {
  color: #b48400;
}
.vip-source-note {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: #5a6880;
}
.benefits-boundary {
  margin: 0;
  padding: 12px 14px;
  font-size: 12.5px;
  line-height: 1.65;
  color: #475164;
  background: #f7f9fd;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 10px;
}
.membership-notes {
  margin-top: 16px;
}
.history-status-cell {
  min-width: 180px;
}
.history-failed-hint {
  margin: 6px 0 0;
  max-width: 260px;
  font-size: 11.5px;
  line-height: 1.55;
  color: #67758a;
}
.orders-help-secondary {
  margin-top: -4px;
}
.order-no-cell {
  min-width: 220px;
}
.order-tag-note {
  margin: 6px 0 0;
  max-width: 240px;
  font-size: 11.5px;
  line-height: 1.55;
  color: #67758a;
  font-family: inherit;
}
.upgrade-btn {
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border-radius: 999px;
  box-shadow: 0 12px 24px rgba(45, 116, 241, 0.18);
}
.quota-section {
  margin-top: 28px;
}
.quota-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.quota-item {
  padding: 14px 16px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 12px;
}
.quota-item .label {
  display: block;
  font-size: 12px;
  color: #67758a;
  margin-bottom: 6px;
}
.quota-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #1e2430;
}
.history-section {
  margin-top: 28px;
}
.history-title {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted-inline {
  font-size: 12px;
  color: #9aa6b8;
}
.orders-section {
  margin-top: 32px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.section-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.refresh {
  padding: 6px 12px;
  font-size: 12px;
  color: #2268f0;
  background: rgba(34, 104, 240, 0.08);
  border: 0;
  border-radius: 999px;
  cursor: pointer;
}
.muted {
  padding: 20px;
  color: #67758a;
  text-align: center;
}
.empty {
  padding: 36px;
  text-align: center;
  background: #f7f9fd;
  border-radius: 14px;
  color: #67758a;
}
.empty-cta {
  display: inline-block;
  margin-top: 10px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border-radius: 999px;
}
.orders-help {
  margin: 0 0 12px;
  color: #67758a;
  font-size: 13px;
  line-height: 1.6;
}
.orders-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 12px 24px rgba(30, 50, 90, 0.05);
  font-size: 13px;
}
.orders-table th,
.orders-table td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid rgba(231, 236, 245, 0.7);
}
.orders-table th {
  background: #f7f9fd;
  font-weight: 700;
  color: #1e2430;
}
.orders-table tbody tr:last-child td {
  border-bottom: 0;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
}
.amount {
  font-weight: 600;
  color: #2268f0;
}
.status {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.status-pending {
  color: #b48400;
  background: #fff4cc;
}
.status-paid {
  color: #1f8f5a;
  background: #e0f5ea;
}
.status-canceled,
.status-expired {
  color: #b8332a;
  background: #fff1ef;
}
.order-tag {
  display: inline-block;
  margin-top: 4px;
  margin-left: 0;
  padding: 2px 6px;
  font-size: 10.5px;
  font-weight: 700;
  border-radius: 4px;
  white-space: nowrap;
}
.mock-tag {
  color: #6b4500;
  background: #fff4cc;
}
.manual-tag {
  color: #1f6b45;
  background: #e0f5ea;
}
.stripe-test-tag {
  color: #1e4f91;
  background: #e8f1ff;
}
.link-btn {
  padding: 4px 10px;
  font-size: 12px;
  color: #2268f0;
  background: rgba(34, 104, 240, 0.08);
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}
.error {
  margin: 0 0 12px;
  padding: 8px 12px;
  font-size: 13px;
  color: #b8332a;
  background: #fff1ef;
  border-radius: 8px;
}
</style>
