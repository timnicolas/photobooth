import { createApp } from 'vue'
import { createPinia } from 'pinia'
import vuetify from './plugins/vuetify'
import router from './router'
import App from './App.vue'
import './styles/layout.css'
import { bindAudioUnlock } from './composables/useAudio'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')

// Resume audio on any user interaction (iOS suspends/interrupts the AudioContext)
bindAudioUnlock()
