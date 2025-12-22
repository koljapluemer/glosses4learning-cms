import { createRouter, createWebHashHistory } from 'vue-router'
import GlossBrowser from './pages/GlossBrowser.vue'
import GlossDetail from './pages/GlossDetail.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'browse',
      component: GlossBrowser
    },
    {
      path: '/gloss/:language/:slug',
      name: 'detail',
      component: GlossDetail,
      props: true
    }
  ]
})
