<script setup>
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()
</script>

<template>
  <section class="result-page">
    <div class="result-card">
      <div class="emoji">🤷</div>
      <h1>{{ t('payment.cancelTitle') }}</h1>
      <p v-if="route.query.order_no">{{ t('payment.cancelWithOrder', { orderNo: route.query.order_no }) }}</p>
      <p v-else>{{ t('payment.cancelGeneric') }}</p>
      <div class="actions">
        <RouterLink class="action primary" to="/account">{{ t('payment.viewMyOrders') }}</RouterLink>
        <RouterLink class="action" to="/pricing">{{ t('payment.backPricing') }}</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.result-page { display: grid; place-items: center; padding: 60px 24px 80px; }
.result-card { width: 100%; max-width: 480px; padding: 40px 32px; background: #fff; border-radius: 18px; border: 1px solid rgba(231,236,245,1); box-shadow: 0 24px 48px rgba(30,50,90,0.06); text-align: center; }
.emoji { font-size: 48px; margin-bottom: 10px; }
h1 { margin: 6px 0 12px; font-size: 22px; font-weight: 700; }
p { margin: 6px 0; font-size: 14px; color: #475164; }
.actions { display: flex; justify-content: center; gap: 12px; margin-top: 22px; flex-wrap: wrap; }
.action { padding: 10px 16px; border-radius: 10px; font-size: 13.5px; font-weight: 600; color: #1e2430; background: #eef2f9; }
.action.primary { color: #fff; background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%); box-shadow: 0 12px 24px rgba(45,116,241,0.18); }
</style>
