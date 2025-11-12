import { createRouter, createWebHistory } from 'vue-router';

const inferBasePath = () => {
  if (typeof window !== 'undefined') {
    const { pathname } = window.location;

    if (pathname.startsWith('/maps_view/')) {
      return '/maps_view/';
    }
  }

  return import.meta.env.BASE_URL || '/';
};

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/components/Dashboard/DashboardView.vue'), // Phase 11 Sprint 2: Full dashboard with sidebar + map
  },
  // Legacy fallback (Sprint 1 map-only view)
  {
    path: '/map',
    name: 'map',
    component: () => import('@/components/MapView.vue'),
  },
  // {
  //   path: '/routes',
  //   name: 'routes',
  //   component: () => import('@/views/RouteBuilder.vue'),
  // },
];

const router = createRouter({
  history: createWebHistory(inferBasePath()),
  routes,
});

export default router;
