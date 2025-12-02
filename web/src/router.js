import { createRouter, createWebHistory } from 'vue-router'
import Home from './pages/Home.vue'
import Workspace from './pages/Workspace.vue'
import Files from './pages/Files.vue'
import Settings from './pages/Settings.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/workspace', name: 'workspace', component: Workspace },
  { path: '/files', name: 'files', component: Files },
  { path: '/settings', name: 'settings', component: Settings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
