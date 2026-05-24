import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import i18n from './i18n'
import router from './router'
import './styles/main.css'

if (typeof window !== 'undefined') {
  if ('scrollRestoration' in window.history) {
    window.history.scrollRestoration = 'manual'
  }
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  if (path === '/') {
    window.scrollTo(0, 0)
  }
}

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)
app.mount('#app')
