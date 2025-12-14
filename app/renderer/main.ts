import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { initSettings } from './entities/system/settingsStore'

const app = createApp(App)
app.use(router)

// Initialize settings before mounting
async function init() {
  await initSettings()
  app.mount('#app')
}

init()
