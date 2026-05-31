<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { fetchOrder } from '../api/client'
import { useUserStore } from '../stores/user'

const { t } = useI18n()
const route = useRoute()
const userStore = useUserStore()

const orderNo = computed(() => String(route.query.order_no || ''))
const order = ref(null)
const loading = ref(true)
const error = ref('')
const polling = ref(null)
const elapsed = ref(0)

const pollOnce = async () => {
  if (!orderNo.value) return
  try {
    const data = await fetchOrder(orderNo.value)
    order.value = data
    if (data.status === 'paid') {
      stopPoll()
      await userStore.refresh()
    } else if (elapsed.value > 30) {
      stopPoll()
    }
  } catch (err) {
    error.value = err.message
  }
}

const stopPoll = () => {
  if (polling.value) {
    window.clearInterval(polling.value)
    polling.value = null
  }
}

onMounted(async () => {
  if (!orderNo.value) {
    error.value = t('payment.orderNoMissing')
    loading.value = false
    return
  }
  await pollOnce()
  loading.value = false
  if (order.value?.status !== 'paid') {
    polling.value = window.setInterval(async () => {
      elapsed.value += 2
      await pollOnce()
    }, 2000)
  }
})

onBeforeUnmount(stopPoll)
</script>

<template>
  <section class="result-page">
    <div class="result-card">
      <div v-if="loading" class="loader">{{ t('payment.checking') }}</div>
      <template v-else>
        <div v-if="order?.status === 'paid'" class="success-state">
          <div class="emoji">🎉</div>
          <h1>{{ t('payment.successTitle') }}</h1>
          <p>{{ t('payment.successOrder', { orderNo: order.order_no }) }}</p>
          <p v-if="!String(order.order_no || '').startsWith('MAN')" class="beta-note">{{ t('payment.successTestModeNote') }}</p>
          <p v-if="userStore.user?.is_lifetime_vip">{{ t('payment.lifetimeGranted') }}</p>
          <p v-else-if="userStore.vipLabel">{{ userStore.vipLabel }}</p>
          <div class="actions">
            <RouterLink class="action primary" to="/">{{ t('payment.backHome') }}</RouterLink>
            <RouterLink class="action" to="/account">{{ t('payment.viewAccount') }}</RouterLink>
          </div>
        </div>

        <div v-else-if="error" class="error-state">
          <div class="emoji">⚠️</div>
          <h1>{{ t('payment.errorTitle') }}</h1>
          <p>{{ error }}</p>
          <RouterLink class="action primary" to="/account">{{ t('payment.goOrders') }}</RouterLink>
        </div>

        <div v-else class="pending-state">
          <div class="emoji">⌛</div>
          <h1>{{ t('payment.pendingTitle') }}</h1>
          <p>{{ t('payment.pendingDesc', { status: order?.status || '—' }) }}</p>
          <p class="hint">{{ t('payment.pendingHint') }}</p>
          <RouterLink class="action" to="/account">{{ t('payment.goOrders') }}</RouterLink>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.result-page {
  display: grid;
  place-items: center;
  padding: 60px 24px 80px;
}
.result-card {
  width: 100%;
  max-width: 520px;
  padding: 40px 32px;
  background: #fff;
  border-radius: 18px;
  border: 1px solid rgba(231, 236, 245, 1);
  box-shadow: 0 24px 48px rgba(30, 50, 90, 0.06);
  text-align: center;
}
.emoji {
  font-size: 48px;
  margin-bottom: 10px;
}
h1 {
  margin: 6px 0 12px;
  font-size: 22px;
  font-weight: 700;
}
p {
  margin: 6px 0;
  font-size: 14px;
  color: #475164;
}
.actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 22px;
}
.action {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 600;
  color: #1e2430;
  background: #eef2f9;
}
.action.primary {
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  box-shadow: 0 12px 24px rgba(45, 116, 241, 0.18);
}
.loader {
  padding: 18px;
  color: #67758a;
}
.hint {
  font-size: 12.5px;
  color: #67758a;
}
.beta-note {
  font-size: 12.5px;
  line-height: 1.6;
  color: #67758a;
}
</style>
