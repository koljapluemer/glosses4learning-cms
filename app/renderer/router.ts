import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('./pages/dashboard/DashboardPage.vue')
    },
    {
      path: '/situation/:situationLang/:situationSlug/:nativeLang/:targetLang',
      name: 'situation-workspace',
      component: () => import('./pages/situation-workspace/SituationWorkspace.vue')
    }
  ]
})

export default router
