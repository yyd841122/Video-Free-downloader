<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getRegisterEmailErrorKey, isRegisterEmailApiError } from '../utils/emailValidation'

const { t } = useI18n()
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const nickname = ref('')
const error = ref('')
const emailError = ref('')
const loading = ref(false)

const emailErrorMessage = (key) => {
  if (key === 'required') return t('auth.emailRequired')
  if (key === 'invalid') return t('auth.emailInvalid')
  if (key === 'placeholder') return t('auth.emailPlaceholderBlocked')
  return ''
}

const validateEmailField = () => {
  const key = getRegisterEmailErrorKey(email.value)
  emailError.value = key ? emailErrorMessage(key) : ''
  return !key
}

const onEmailInput = () => {
  if (emailError.value) {
    validateEmailField()
  }
}

const submit = async () => {
  error.value = ''
  emailError.value = ''
  if (!validateEmailField()) {
    return
  }
  if ((password.value || '').length < 6) {
    error.value = t('auth.passwordMin')
    return
  }
  loading.value = true
  try {
    await userStore.register(email.value.trim(), password.value, nickname.value.trim() || undefined)
    const target = route.query.redirect || '/'
    router.push(target)
  } catch (err) {
    const message = err.message || t('auth.registerFailed')
    if (isRegisterEmailApiError(message)) {
      emailError.value = message
    } else {
      error.value = message
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-section">
    <div class="auth-card">
      <h1>{{ t('auth.registerTitle') }}</h1>
      <p class="auth-subtitle">{{ t('auth.registerSubtitle') }}</p>

      <form class="auth-form" @submit.prevent="submit">
        <label :class="{ 'has-error': emailError }">
          <span>{{ t('auth.email') }}</span>
          <input
            v-model="email"
            type="email"
            autocomplete="username"
            :placeholder="t('auth.emailPlaceholder')"
            required
            maxlength="254"
            :aria-invalid="emailError ? 'true' : 'false'"
            @input="onEmailInput"
            @blur="validateEmailField"
          />
          <p class="auth-field-hint">{{ t('auth.registerEmailHint') }}</p>
          <p v-if="emailError" class="auth-field-error">{{ emailError }}</p>
        </label>
        <label>
          <span>{{ t('auth.nicknameOptional') }}</span>
          <input
            v-model="nickname"
            type="text"
            autocomplete="nickname"
            :placeholder="t('auth.nicknamePlaceholder')"
            maxlength="32"
          />
        </label>
        <label>
          <span>{{ t('auth.password') }}</span>
          <input
            v-model="password"
            type="password"
            autocomplete="new-password"
            :placeholder="t('auth.passwordPlaceholder')"
            required
            minlength="6"
          />
        </label>
        <p v-if="error" class="auth-error">{{ error }}</p>
        <p class="auth-agree">
          {{ t('auth.agreeTerms') }}
          <RouterLink to="/legal/terms" target="_blank">{{ t('auth.termsLink') }}</RouterLink>
          {{ t('auth.and') }}
          <RouterLink to="/legal/privacy" target="_blank">{{ t('auth.privacyLink') }}</RouterLink>
        </p>
        <button type="submit" class="auth-submit" :disabled="loading">
          {{ loading ? t('auth.registerSubmitting') : t('auth.registerSubmit') }}
        </button>
      </form>

      <p class="auth-foot">
        {{ t('auth.hasAccount') }}
        <RouterLink :to="{ name: 'login', query: $route.query }">{{ t('auth.loginNow') }}</RouterLink>
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
.auth-form label.has-error input {
  border-color: #e85d4d;
  background: #fff8f7;
}
.auth-form input {
  width: 100%;
  padding: 11px 14px;
  font-size: 14px;
  color: #1e2430;
  background: #f7f9fd;
  border: 1px solid rgba(34, 104, 240, 0.12);
  border-radius: 10px;
}
.auth-form input:focus {
  outline: none;
  background: #fff;
  border-color: #2268f0;
}
.auth-field-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #67758a;
  font-weight: 400;
}
.auth-field-error {
  margin: 0;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.45;
  color: #b8332a;
  background: #fff1ef;
  border-radius: 8px;
  font-weight: 500;
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
.auth-agree {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.5;
  color: #67758a;
}
.auth-agree a {
  color: #2268f0;
  font-weight: 600;
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
