<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { fetchOrder, mockPay } from '../api/client'
import { useUserStore } from '../stores/user'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const orderNo = computed(() => String(route.query.order_no || ''))
const order = ref(null)
const loading = ref(true)
const error = ref('')
const submitting = ref('')

onMounted(async () => {
  if (!orderNo.value) {
    error.value = t('payment.orderMissing')
    loading.value = false
    return
  }
  try {
    order.value = await fetchOrder(orderNo.value)
  } catch (err) {
    error.value = err.message || t('payment.orderLoadFailed')
  } finally {
    loading.value = false
  }
})

const pay = async (outcome) => {
  submitting.value = outcome
  error.value = ''
  try {
    const updated = await mockPay(orderNo.value, outcome)
    order.value = updated
    if (outcome === 'success') {
      await userStore.refresh()
      router.push({ name: 'payment-success', query: { order_no: orderNo.value } })
    } else if (outcome === 'cancel') {
      router.push({ name: 'payment-cancel', query: { order_no: orderNo.value } })
    }
  } catch (err) {
    error.value = err.message || t('payment.actionFailed')
  } finally {
    submitting.value = ''
  }
}
</script>

<template>
  <section class="mock-pay">
    <div class="mock-card">
      <div class="mock-header">
        <span class="mock-tag">{{ t('payment.mockTag') }}</span>
        <h1>{{ t('payment.mockTitle') }}</h1>
        <p>{{ t('payment.mockDesc') }}</p>
      </div>

      <p v-if="loading" class="muted">{{ t('payment.orderLoading') }}</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <div v-if="order" class="order-summary">
        <div class="row">
          <span>{{ t('payment.labelOrderNo') }}</span>
          <strong class="mono">{{ order.order_no }}</strong>
        </div>
        <div class="row">
          <span>{{ t('payment.labelPlan') }}</span>
          <strong>{{ order.plan_name }}</strong>
        </div>
        <div class="row">
          <span>{{ t('payment.labelAmount') }}</span>
          <strong class="amount">{{ order.amount_display }}</strong>
        </div>
        <div class="row">
          <span>{{ t('payment.labelStatus') }}</span>
          <strong :class="`status status-${order.status}`">{{ order.status }}</strong>
        </div>
      </div>

      <div v-if="order && order.status === 'pending'" class="actions">
        <button class="action success" :disabled="submitting === 'success'" @click="pay('success')">
          ✅ {{ t('payment.mockSuccess') }}
        </button>
        <button class="action fail" :disabled="submitting === 'fail'" @click="pay('fail')">
          ❌ {{ t('payment.mockFail') }}
        </button>
        <button class="action cancel" :disabled="submitting === 'cancel'" @click="pay('cancel')">
          ↩︎ {{ t('payment.mockCancel') }}
        </button>
      </div>

      <div v-else-if="order && order.status === 'paid'" class="paid-tip">
        {{ t('payment.paidDone') }}
        <RouterLink to="/account">{{ t('payment.goAccount') }}</RouterLink>
      </div>
      <div v-else-if="order" class="paid-tip">
        {{ t('payment.cannotPay', { status: order.status }) }}
        <RouterLink to="/pricing">{{ t('payment.reorder') }}</RouterLink>
      </div>

      <p class="tip">{{ t('payment.stripeTip') }}</p>
    </div>
  </section>
</template>

<style scoped>
.mock-pay {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}
.mock-card {
  padding: 36px 32px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(30, 50, 90, 0.06);
}
.mock-header h1 {
  margin: 8px 0 12px;
  font-size: 24px;
  font-weight: 700;
}
.mock-header p {
  margin: 0 0 24px;
  color: #67758a;
  font-size: 13.5px;
  line-height: 1.7;
}
.mock-tag {
  display: inline-block;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 700;
  color: #6b4500;
  background: #fff4cc;
  border-radius: 999px;
}
.muted {
  color: #67758a;
}
.error {
  color: #b8332a;
  background: #fff1ef;
  padding: 10px 12px;
  border-radius: 10px;
}
.order-summary {
  margin: 16px 0 24px;
  padding: 18px 20px;
  background: #f7f9fd;
  border-radius: 12px;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.row:last-child {
  border-bottom: 0;
}
.row span {
  color: #67758a;
}
.row strong {
  color: #1e2430;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}
.amount {
  color: #2268f0;
  font-size: 16px;
}
.status {
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.4px;
}
.status-pending {
  color: #b48400;
}
.status-paid {
  color: #1f8f5a;
}
.status-canceled,
.status-expired {
  color: #b8332a;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
}
.action {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 700;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  transition: filter 0.15s, transform 0.15s;
}
.action:hover {
  filter: brightness(1.04);
}
.action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.success {
  color: #fff;
  background: linear-gradient(135deg, #34c98c 0%, #1f8f5a 100%);
  box-shadow: 0 12px 24px rgba(31, 143, 90, 0.2);
}
.fail {
  color: #fff;
  background: linear-gradient(135deg, #ff6b5b 0%, #d4382c 100%);
  box-shadow: 0 12px 24px rgba(212, 56, 44, 0.2);
}
.cancel {
  color: #1e2430;
  background: #eef2f9;
}
.paid-tip {
  padding: 14px 16px;
  font-size: 14px;
  color: #1e2430;
  background: #eef7f1;
  border-radius: 10px;
  margin-bottom: 18px;
}
.paid-tip a {
  margin-left: 8px;
  color: #2268f0;
  font-weight: 600;
}
.tip {
  margin: 0;
  font-size: 12.5px;
  color: #67758a;
}
.tip code {
  padding: 2px 6px;
  font-size: 12px;
  background: #f7f9fd;
  border-radius: 6px;
}
</style>
