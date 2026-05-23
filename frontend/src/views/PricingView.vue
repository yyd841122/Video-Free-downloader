<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { createCheckout, fetchBillingMode, fetchPlans } from '../api/client'
import { useUserStore } from '../stores/user'

const { t } = useI18n()
const userStore = useUserStore()
const router = useRouter()

const plans = ref([])
const loading = ref(true)
const error = ref('')
const checkoutLoading = ref('')
const billingMode = ref({ mock: true })

const benefits = computed(() => [
  { label: t('pricing.benefitQuality'), free: t('pricing.freeQuality'), vip: t('pricing.vipQuality') },
  { label: t('pricing.benefitAi'), free: t('pricing.freeAi'), vip: t('pricing.vipAi') },
  { label: t('pricing.benefitChat'), free: t('pricing.freeChat'), vip: t('pricing.vipChat') },
  { label: t('pricing.benefitBatch'), free: t('pricing.dash'), vip: '✔' },
  { label: t('pricing.benefitHistory'), free: t('pricing.dash'), vip: t('pricing.vipHistory') },
  { label: t('pricing.benefitRedownload'), free: t('pricing.dash'), vip: t('pricing.vipRedownload') },
  { label: t('pricing.benefitConcurrent'), free: t('pricing.freeConcurrent'), vip: t('pricing.vipConcurrent') },
  { label: t('pricing.benefitPriority'), free: t('pricing.dash'), vip: '✔' },
])

const vipExpireText = computed(() => {
  if (!userStore.isVip) return ''
  if (userStore.user?.is_lifetime_vip) return t('pricing.lifetimeNoRenew')
  return userStore.vipLabel
})

onMounted(async () => {
  try {
    const [planList, mode] = await Promise.all([fetchPlans(), fetchBillingMode()])
    plans.value = planList
    billingMode.value = mode
  } catch (err) {
    error.value = err.message || t('pricing.loadFailed')
  } finally {
    loading.value = false
  }
})

const buy = async (planCode) => {
  if (!userStore.isLoggedIn) {
    router.push({ name: 'login', query: { redirect: '/pricing' } })
    return
  }
  error.value = ''
  checkoutLoading.value = planCode
  try {
    const data = await createCheckout(planCode)
    if (data.mode === 'mock') {
      router.push({ name: 'mock-pay', query: { order_no: data.order_no } })
    } else {
      window.location.href = data.checkout_url
    }
  } catch (err) {
    error.value = err.message || t('pricing.checkoutFailed')
  } finally {
    checkoutLoading.value = ''
  }
}
</script>

<template>
  <section class="pricing-page">
    <header class="pricing-hero">
      <h1>{{ t('pricing.title') }}</h1>
      <p>{{ t('pricing.subtitle') }}</p>
      <p v-if="vipExpireText" class="vip-current">{{ vipExpireText }}</p>
      <p v-if="billingMode.mock" class="mode-tip">{{ t('pricing.mockModeTip') }}</p>
    </header>

    <p v-if="error" class="pricing-error">{{ error }}</p>

    <div v-if="loading" class="pricing-loading">{{ t('pricing.loading') }}</div>

    <div v-else class="plan-card-grid">
      <article
        v-for="plan in plans"
        :key="plan.code"
        :class="['pricing-card', { recommended: plan.recommended, lifetime: plan.is_lifetime }]"
      >
        <span v-if="plan.recommended" class="badge">{{ t('pricing.badgePopular') }}</span>
        <span v-else-if="plan.is_lifetime" class="badge gold">{{ t('pricing.badgeLifetime') }}</span>
        <h3>{{ plan.name }}</h3>
        <p class="desc">{{ plan.description }}</p>
        <div class="price-row">
          <strong>{{ plan.price_display }}</strong>
          <span v-if="!plan.is_lifetime">/ {{ plan.duration_days }} {{ t('pricing.daysSuffix') }}</span>
          <span v-else>/ {{ t('pricing.foreverSuffix') }}</span>
        </div>
        <button
          class="buy-button"
          type="button"
          :disabled="checkoutLoading === plan.code"
          @click="buy(plan.code)"
        >
          {{
            checkoutLoading === plan.code
              ? t('pricing.processing')
              : userStore.isVip
                ? t('pricing.renewNow')
                : t('pricing.buyNow')
          }}
        </button>
      </article>
    </div>

    <section class="benefit-table-wrap">
      <h2>{{ t('pricing.compareTitle') }}</h2>
      <table class="benefit-table">
        <thead>
          <tr>
            <th>{{ t('pricing.colFeature') }}</th>
            <th>{{ t('pricing.colFree') }}</th>
            <th class="vip-col">{{ t('pricing.colVip') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in benefits" :key="row.label">
            <td>{{ row.label }}</td>
            <td>{{ row.free }}</td>
            <td class="vip-col">{{ row.vip }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="trust">
      <h2>{{ t('pricing.trustTitle') }}</h2>
      <ul>
        <li>{{ t('pricing.trust1') }}</li>
        <li>{{ t('pricing.trust2') }}</li>
        <li>{{ t('pricing.trust3') }}</li>
        <li>{{ t('pricing.trust4') }}</li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.pricing-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}
.pricing-hero {
  text-align: center;
  margin-bottom: 36px;
}
.pricing-hero h1 {
  margin: 0 0 12px;
  font-size: 32px;
  font-weight: 700;
}
.pricing-hero p {
  margin: 4px 0;
  color: #67758a;
  font-size: 14px;
}
.vip-current {
  color: #2268f0 !important;
  font-weight: 600;
}
.mode-tip {
  display: inline-block;
  margin-top: 12px !important;
  padding: 8px 14px;
  font-size: 12.5px;
  color: #6b4500;
  background: #fff4cc;
  border-radius: 999px;
}
.pricing-error {
  margin: 0 auto 20px;
  max-width: 600px;
  padding: 10px 14px;
  font-size: 13px;
  color: #b8332a;
  background: #fff1ef;
  border-radius: 10px;
  text-align: center;
}
.pricing-loading {
  text-align: center;
  padding: 40px;
  color: #67758a;
}
.plan-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 56px;
}
.pricing-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 28px 22px 26px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 16px;
  box-shadow: 0 18px 36px rgba(30, 50, 90, 0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}
.pricing-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 22px 44px rgba(30, 50, 90, 0.08);
}
.pricing-card.recommended {
  border-color: #2268f0;
  box-shadow: 0 22px 44px rgba(45, 116, 241, 0.18);
}
.pricing-card.lifetime {
  border-color: #f5c100;
  background: linear-gradient(180deg, #fffaea 0%, #fff 50%);
}
.badge {
  position: absolute;
  top: -12px;
  right: 20px;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border-radius: 999px;
}
.badge.gold {
  background: linear-gradient(135deg, #ffb800 0%, #f59e0b 100%);
}
.pricing-card h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.desc {
  margin: 0;
  color: #67758a;
  font-size: 13px;
}
.price-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.price-row strong {
  font-size: 28px;
  font-weight: 700;
  color: #1e2430;
}
.price-row span {
  font-size: 12.5px;
  color: #67758a;
}
.buy-button {
  margin-top: auto;
  padding: 11px 16px;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(45, 116, 241, 0.18);
}
.lifetime .buy-button {
  background: linear-gradient(135deg, #ffb800 0%, #f59e0b 100%);
  box-shadow: 0 12px 24px rgba(245, 158, 11, 0.25);
  color: #5a3a00;
}
.buy-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.benefit-table-wrap {
  margin: 56px 0;
}
.benefit-table-wrap h2 {
  margin: 0 0 20px;
  font-size: 22px;
  font-weight: 700;
  text-align: center;
}
.benefit-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 12px 24px rgba(30, 50, 90, 0.05);
}
.benefit-table th,
.benefit-table td {
  padding: 14px 18px;
  text-align: left;
  font-size: 14px;
  border-bottom: 1px solid rgba(231, 236, 245, 0.7);
}
.benefit-table th {
  background: #f7f9fd;
  color: #1e2430;
  font-weight: 700;
}
.benefit-table td.vip-col,
.benefit-table th.vip-col {
  color: #2268f0;
  font-weight: 600;
  background: rgba(34, 104, 240, 0.04);
}
.benefit-table tbody tr:last-child td {
  border-bottom: 0;
}
.trust {
  padding: 28px 32px;
  background: #f7f9fd;
  border-radius: 16px;
}
.trust h2 {
  margin: 0 0 14px;
  font-size: 18px;
  font-weight: 700;
}
.trust ul {
  margin: 0;
  padding-left: 20px;
  color: #475164;
  font-size: 13.5px;
  line-height: 1.8;
}
</style>
