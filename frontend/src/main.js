import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import ToastPlugin from './plugins/toast'

const app = createApp(App)
app.use(router)
app.use(ToastPlugin)
app.mount('#app')
