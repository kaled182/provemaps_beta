import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: '/dashboard',
  },
  // Fase 7: Add Dashboard and RouteBuilder routes
  // {
  //   path: '/dashboard',
  //   name: 'dashboard',
  //   component: () => import('@/views/Dashboard.vue'),
  // },
  // {
  //   path: '/routes',
  //   name: 'routes',
  //   component: () => import('@/views/RouteBuilder.vue'),
  // },
];

const router = createRouter({
  history: createWebHistory('/'),
  routes,
});

export default router;
