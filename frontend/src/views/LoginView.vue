<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const { t } = useI18n()
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const submit = async () => {
  error.value = ''
  if (!email.value.trim() || !password.value) {
    error.value = t('auth.loginRequired')
    return
  }
  loading.value = true
  try {
    await userStore.login(email.value.trim(), password.value)
    const target = route.query.redirect || '/'
    router.push(target)
  } catch (err) {
    error.value = err.message || t('auth.loginFailed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-section">
    <div class="auth-card">
      <h1>{{ t('auth.loginTitle') }}</h1>
      <p class="auth-subtitle">{{ t('auth.loginSubtitle') }}</p>

      <form class="auth-form" @submit.prevent="submit">
        <label>
          <span>{{ t('auth.email') }}</span>
          <input v-model="email" type="email" autocomplete="username" :placeholder="t('auth.emailPlaceholder')" required />
        </label>
        <label>
          <span>{{ t('auth.password') }}</span>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            :placeholder="t('auth.passwordPlaceholder')"
            required
            minlength="6"
          />
        </label>
        <p v-if="error" class="auth-error">{{ error }}</p>
        <button type="submit" class="auth-submit" :disabled="loading">
          {{ loading ? t('auth.loginSubmitting') : t('auth.loginSubmit') }}
        </button>
      </form>

      <p class="auth-foot">
        {{ t('auth.noAccount') }}
        <RouterLink :to="{ name: 'register', query: $route.query }">{{ t('auth.registerNow') }}</RouterLink>
      </p>
    </div>
  </section>
</template>

<style scoped>
.auth-section {
  display: grid;
  place-items: center;
  padding: 48px 16px 80px;
}
.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px 28px;
  background: #fff;
  border: 1px solid rgba(231, 236, 245, 1);
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(30, 50, 90, 0.06);
}
.auth-card h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #1e2430;
}
.auth-subtitle {
  margin: 0 0 24px;
  font-size: 13px;
  color: #67758a;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.auth-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #475164;
  font-weight: 600;
}
.auth-form input {
  width: 100%;
  padding: 11px 14px;
  font-size: 14px;
  color: #1e2430;
  background: #f7f9fd;
  border: 1px solid rgba(34, 104, 240, 0.12);
  border-radius: 10px;
  transition: border 0.2s, background 0.2s;
}
.auth-form input:focus {
  outline: none;
  background: #fff;
  border-color: #2268f0;
}
.auth-error {
  margin: 0;
  padding: 10px 12px;
  font-size: 13px;
  color: #b8332a;
  background: #fff1ef;
  border-radius: 10px;
}
.auth-submit {
  margin-top: 4px;
  padding: 12px 18px;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #4d90ff 0%, #2268f0 100%);
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 16px 28px rgba(45, 116, 241, 0.18);
}
.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.auth-foot {
  margin: 24px 0 0;
  font-size: 13px;
  color: #67758a;
  text-align: center;
}
.auth-foot a {
  color: #2268f0;
  font-weight: 600;
}
</style>
