import { createRouter, createWebHistory } from 'vue-router'
import i18n from '../i18n'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue'), meta: { titleKey: 'meta.home' } },
  { path: '/pricing', name: 'pricing', component: () => import('../views/PricingView.vue'), meta: { titleKey: 'meta.pricing' } },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { titleKey: 'meta.login' } },
  { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue'), meta: { titleKey: 'meta.register' } },
  {
    path: '/account',
    name: 'account',
    component: () => import('../views/AccountView.vue'),
    meta: { titleKey: 'meta.account', requiresAuth: true },
  },
  {
    path: '/mock-pay',
    name: 'mock-pay',
    component: () => import('../views/MockPayView.vue'),
    meta: { titleKey: 'meta.mockPay', requiresAuth: true },
  },
  {
    path: '/payment/success',
    name: 'payment-success',
    component: () => import('../views/PaymentSuccessView.vue'),
    meta: { titleKey: 'meta.paymentSuccess', requiresAuth: true },
  },
  {
    path: '/payment/cancel',
    name: 'payment-cancel',
    component: () => import('../views/PaymentCancelView.vue'),
    meta: { titleKey: 'meta.paymentCancel', requiresAuth: true },
  },
  {
    path: '/legal/privacy',
    name: 'legal-privacy',
    component: () => import('../views/LegalView.vue'),
    meta: { titleKey: 'meta.privacy', legalKey: 'privacy' },
  },
  {
    path: '/legal/terms',
    name: 'legal-terms',
    component: () => import('../views/LegalView.vue'),
    meta: { titleKey: 'meta.terms', legalKey: 'terms' },
  },
  {
    path: '/legal/copyright',
    name: 'legal-copyright',
    component: () => import('../views/LegalView.vue'),
    meta: { titleKey: 'meta.copyright', legalKey: 'copyright' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  if (!userStore.initialized) {
    await userStore.refresh()
  }
  if (to.meta?.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

router.afterEach((to) => {
  if (to.meta?.titleKey && typeof document !== 'undefined') {
    document.title = `${i18n.global.t(to.meta.titleKey)} · SaveAny`
  }
})

export default router
