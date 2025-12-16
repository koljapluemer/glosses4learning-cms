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
      path: '/pick-situation',
      name: 'pick-situation',
      component: () => import('./pages/pick-situation/PickSituation.vue')
    },
    {
      path: '/situation/:situationLang/:situationSlug',
      name: 'situation-workspace',
      component: () => import('./pages/situation-workspace/SituationWorkspace.vue')
    }
  ]
})

export default router
