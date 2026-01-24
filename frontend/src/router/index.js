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
    if (pathname.startsWith('/Network/')) {
      return '/';
    }
    if (pathname.startsWith('/NetworkDesign/')) {
      return '/';
    }
    if (pathname.startsWith('/setup/')) {
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
    component: () => import('@/views/monitoring/CustomMapsManager.vue'),
  },
  {
    path: '/monitoring/:category/map/:mapId',
    name: 'custom-map-viewer',
    component: () => import('@/views/monitoring/CustomMapViewer.vue'),
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
    path: '/Network/NetworkDesign/',
    name: 'network-design',
    component: () => import('@/components/NetworkDesign/NetworkDesignView.vue'),
  },
  {
    path: '/Network/DeviceImport/',
    name: 'device-import',
    component: () => import('@/components/DeviceImport/DeviceImportManager.vue'),
  },
  {
    path: '/network/inventory',
    name: 'inventory',
    component: () => import('@/components/Inventory/InventoryView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Inventário de Rede',
    },
  },
  {
    path: '/network/inventory/:id',
    name: 'inventory-detail',
    component: () => import('@/components/Inventory/InventoryDetailView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Detalhe do Site',
    },
  },
  {
    path: '/setup/config',
    name: 'setup-config',
    component: () => import('@/views/ConfigurationPage.vue'),
  },
  {
    path: '/video/cameras',
    name: 'video-cameras',
    component: () => import('@/views/video/VideoCamerasView.vue'),
  },
  {
    path: '/video/mosaics',
    name: 'video-mosaics',
    component: () => import('@/views/video/VideoMosaicsView.vue'),
  },
  {
    path: '/video/mosaics/:id',
    name: 'mosaic-viewer',
    component: () => import('@/views/video/MosaicViewerView.vue'),
  },
  {
    path: '/video/groups',
    name: 'video-groups',
    component: () => import('@/views/video/VideoGroupsView.vue'),
  },
  {
    path: '/metrics/health',
    name: 'system-health',
    component: () => import('@/views/SystemHealthView.vue'),
  },
  {
    path: '/docs',
    name: 'docs',
    component: () => import('@/views/DocsView.vue'),
  },
  {
    path: '/system/users',
    name: 'users-management',
    component: () => import('@/views/UsersManagement.vue'),
  },
  {
    path: '/profile',
    name: 'user-profile',
    component: () => import('@/views/UserProfile.vue'),
  },
  {
    path: '/meu-cadastro',
    name: 'my-registration',
    component: () => import('@/views/MyRegistration.vue'),
  },
  // Legacy redirects
  {
    path: '/setup_app/config',
    redirect: '/setup/config',
  },
  {
    path: '/NetworkDesign/',
    redirect: '/Network/NetworkDesign/',
  },
  {
    path: '/zabbix/lookup/',
    redirect: '/Network/DeviceImport/',
  },
  // Legacy fallback (Sprint 1 map-only view)
  {
    path: '/map',
    name: 'map',
    component: () => import('@/components/MapView.vue'),
  },
  {
    path: '/network/design/fiber/:id',
    name: 'FiberRouteEditor',
    component: () => import('@/features/networkDesign/FiberRouteEditor.vue'),
    props: true,
    meta: { title: 'Editor de Traçado' },
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
