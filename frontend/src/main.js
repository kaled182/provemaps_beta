import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { setupGlobalErrorHandler } from './composables/useErrorHandler';
// Tailwind e FontAwesome compilados/auto-hospedados — sem CDN (EV-0019, CLAUDE.md §2.8).
import './design-system/tokens.css'; // ADR 0007 Fase 1: tokens + fontes (EV-0028)
import './assets/tailwind.css';
import '@fortawesome/fontawesome-free/css/all.min.css';
import './assets/site-details-modal.css';

const app = createApp(App);

app.use(createPinia());
app.use(router);

// Setup global error handling
setupGlobalErrorHandler(app);

app.mount('#app');
