import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { setupGlobalErrorHandler } from './composables/useErrorHandler';
import './assets/site-details-modal.css';

const app = createApp(App);

app.use(createPinia());
app.use(router);

// Setup global error handling
setupGlobalErrorHandler(app);

app.mount('#app');
