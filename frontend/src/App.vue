<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import { useUserStore } from './stores/user'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()
const menuOpen = ref(false)

onMounted(async () => {
  if (!userStore.initialized) {
    await userStore.refresh()
  }
})

const greetName = computed(() => {
  const u = userStore.user
  if (!u) return ''
  return u.nickname || (u.email || '').split('@')[0]
})

const avatarInitial = computed(() => (greetName.value ? greetName.value[0].toUpperCase() : '?'))

const toggleMenu = () => {
  menuOpen.value = !menuOpen.value
}

const closeMenu = () => {
  menuOpen.value = false
}

const handleLogout = () => {
  userStore.logout()
  closeMenu()
  router.push('/')
}

const SUPPORT_EMAIL = 'support@cozyguidehub.com'
const SUPPORT_MAILTO = `mailto:${SUPPORT_EMAIL}`
</script>

<template>
  <div class="page-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" @click="closeMenu">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" role="img">
            <path d="M9.75 8.5 15.5 12l-5.75 3.5v-7Z" />
            <rect x="4.5" y="4.5" width="15" height="15" rx="5.5" />
          </svg>
        </span>
        <span class="brand-name">SaveAny</span>
        <span class="brand-badge">{{ t('nav.brandBadge') }}</span>
      </RouterLink>

      <nav class="nav-links" :aria-label="t('nav.main')">
        <RouterLink to="/">{{ t('nav.download') }}</RouterLink>
        <RouterLink to="/pricing">{{ t('nav.pricing') }}</RouterLink>
        <RouterLink v-if="userStore.isLoggedIn" to="/account">{{ t('nav.account') }}</RouterLink>
      </nav>

      <div class="auth-area">
        <LanguageSwitcher />
        <template v-if="!userStore.isLoggedIn">
          <RouterLink class="auth-link" to="/login">{{ t('nav.login') }}</RouterLink>
          <RouterLink class="auth-link primary" to="/register">{{ t('nav.register') }}</RouterLink>
        </template>
        <template v-else>
          <RouterLink v-if="!userStore.isVip" class="vip-button" to="/pricing">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.9-5.4 2.9 1-6-4.4-4.3 6.1-.9L12 3Z" />
            </svg>
            {{ t('nav.upgradeVip') }}
          </RouterLink>
          <span v-else class="vip-badge" :title="t('nav.vip')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.9-5.4 2.9 1-6-4.4-4.3 6.1-.9L12 3Z" />
            </svg>
            {{ userStore.user.is_lifetime_vip ? t('nav.lifetimeVip') : t('nav.vip') }}
          </span>
          <div class="user-dropdown">
            <button class="avatar-button" type="button" @click="toggleMenu" :aria-expanded="menuOpen">
              <span class="avatar">{{ avatarInitial }}</span>
              <span class="user-name">{{ greetName }}</span>
            </button>
            <div v-if="menuOpen" class="user-dropdown-menu" @click="closeMenu">
              <RouterLink to="/account">{{ t('nav.account') }}</RouterLink>
              <RouterLink to="/pricing">{{ userStore.isVip ? t('nav.renewVip') : t('nav.upgradeVip') }}</RouterLink>
              <button type="button" @click="handleLogout">{{ t('nav.logout') }}</button>
            </div>
          </div>
        </template>
      </div>
    </header>

    <main>
      <RouterView />
    </main>

    <footer class="site-footer">
      <p class="footer-tagline">{{ t('footer.tagline') }}</p>
      <nav class="footer-links" :aria-label="t('footer.tagline')">
        <RouterLink to="/legal/privacy">{{ t('footer.privacy') }}</RouterLink>
        <RouterLink to="/legal/terms">{{ t('footer.terms') }}</RouterLink>
        <RouterLink to="/legal/copyright">{{ t('footer.copyright') }}</RouterLink>
        <a :href="SUPPORT_MAILTO">{{ t('footer.contactWithEmail', { email: SUPPORT_EMAIL }) }}</a>
      </nav>
      <p class="footer-rights">{{ t('footer.rights', { year: new Date().getFullYear() }) }}</p>
    </footer>
  </div>
</template>

<style>
.auth-area {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-self: end;
}

.auth-link {
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #1e2430;
  border-radius: 999px;
  transition: background 0.2s;
}

.auth-link:hover {
  background: rgba(34, 104, 240, 0.08);
}

.auth-link.primary {
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  box-shadow: 0 10px 22px rgba(45, 116, 241, 0.18);
}

.auth-link.primary:hover {
  filter: brightness(1.05);
}

.vip-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #6b4500;
  background: linear-gradient(135deg, #fff4cc 0%, #ffd87a 100%);
  border-radius: 999px;
  box-shadow: 0 6px 16px rgba(255, 196, 0, 0.25);
}

.vip-badge svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
  stroke: none;
}

.user-dropdown {
  position: relative;
}

.avatar-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(34, 104, 240, 0.12);
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s;
}

.avatar-button:hover {
  background: rgba(34, 104, 240, 0.06);
}

.avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border-radius: 50%;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e2430;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 160px;
  padding: 6px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 12px;
  box-shadow: 0 18px 36px rgba(30, 50, 90, 0.12);
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 50;
}

.user-dropdown-menu a,
.user-dropdown-menu button {
  display: block;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  color: #1e2430;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.user-dropdown-menu a:hover,
.user-dropdown-menu button:hover {
  background: rgba(34, 104, 240, 0.06);
  color: #2268f0;
}

.nav-links a.router-link-active {
  color: #2268f0;
}

.site-footer {
  margin-top: 48px;
  padding: 28px 24px 36px;
  text-align: center;
  border-top: 1px solid rgba(231, 236, 245, 1);
  background: rgba(255, 255, 255, 0.6);
}

.footer-tagline {
  margin: 0 0 12px;
  font-size: 13px;
  color: #67758a;
}

.footer-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
}

.footer-links a {
  font-size: 13px;
  font-weight: 600;
  color: #2268f0;
}

.footer-links a:hover {
  text-decoration: underline;
}

.footer-rights {
  margin: 0;
  font-size: 12px;
  color: #9aa6b8;
}
</style>
