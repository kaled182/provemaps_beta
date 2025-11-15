import { createRouter, createWebHistory } from 'vue-router';

const inferBasePath = () => {
  if (typeof window !== 'undefined') {
    const { pathname } = window.location;

    if (pathname.startsWith('/maps_view/')) {
      return '/maps_view/';
    }
    if (pathname.startsWith('/monitoring/')) {
      return '/';
    }
    if (pathname.startsWith('/NetworkDesign/')) {
      return '/';
    }
    if (pathname.startsWith('/static/vue-spa/')) {
      return '/';
    }
  }

  return '/';
};

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: '/monitoring/monitoring-all',
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/components/Dashboard/DashboardView.vue'), // Phase 11 Sprint 2: Full dashboard with sidebar + map
  },
  {
    path: '/monitoring/monitoring-all',
    name: 'monitoring-all',
    component: () => import('@/components/Monitoring/MonitoringOverview.vue'),
  },
  {
    path: '/monitoring/backbone',
    name: 'monitoring-backbone',
    component: () => import('@/components/Dashboard/DashboardView.vue'),
  },
  {
    path: '/monitoring/gpon',
    name: 'monitoring-gpon',
    component: () => import('@/components/Monitoring/MonitoringGpon.vue'),
  },
  {
    path: '/monitoring/dwdm',
    name: 'monitoring-dwdm',
    component: () => import('@/components/Monitoring/MonitoringDwdm.vue'),
  },
  {
    path: '/NetworkDesign/',
    name: 'network-design',
    component: () => import('@/components/NetworkDesign/NetworkDesignView.vue'),
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

const resolvedBase = inferBasePath();

if (typeof window !== 'undefined') {
  console.log('[Router] Base path resolved to', resolvedBase, 'for location', window.location.pathname);
}

const router = createRouter({
  history: createWebHistory(resolvedBase),
  routes,
});

export default router;
