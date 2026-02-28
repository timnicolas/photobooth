import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import PhotoboothView from '../views/PhotoboothView.vue'
import GalleryView from '../views/GalleryView.vue'
import AdminView from '../views/AdminView.vue'

const routes = [
  { path: '/', component: PhotoboothView, meta: { requiresAuth: true } },
  { path: '/login', component: LoginView },
  { path: '/gallery', component: GalleryView, meta: { requiresAuth: true } },
  { path: '/admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) return '/login'
  if (to.meta.requiresAdmin) {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (!user.is_admin) return '/'
  }
})

export default router
