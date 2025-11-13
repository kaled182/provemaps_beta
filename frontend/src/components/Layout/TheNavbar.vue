<template>
  <nav class="bg-gray-800 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo e Título -->
        <div class="flex items-center">
          <div class="h-10 w-10 mr-3 rounded-full bg-blue-600 flex items-center justify-center">
            <span class="text-white font-bold text-lg">PM</span>
          </div>
          <span class="font-bold text-xl tracking-tight">ProveMaps</span>
        </div>

        <!-- Menu de Navegação -->
        <div class="flex items-center space-x-1">
          <a 
            href="/maps_view/dashboard/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/maps_view/dashboard/') }"
          >
            Dashboard
          </a>
          <a 
            href="/setup/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/setup/') }"
          >
            Setup
          </a>
          <a 
            href="/admin/" 
            class="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-700 transition-colors"
            :class="{ 'bg-gray-900': isActive('/admin/') }"
            target="_blank"
          >
            Admin
          </a>
          
          <!-- Botão Logout -->
          <form 
            action="/accounts/logout/" 
            method="post" 
            class="inline ml-2"
          >
            <input 
              type="hidden" 
              name="csrfmiddlewaretoken" 
              :value="csrfToken"
            >
            <button 
              type="submit" 
              class="px-3 py-2 rounded-md text-sm font-medium bg-red-600 hover:bg-red-700 transition-colors"
            >
              Sair
            </button>
          </form>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue';

const csrfToken = ref(window.CSRF_TOKEN || '');

function isActive(path) {
  return window.location.pathname.startsWith(path);
}
</script>

<style scoped>
/* Animações suaves */
nav a, nav button {
  transition: all 0.2s ease-in-out;
}

nav a:hover, nav button:hover {
  transform: translateY(-1px);
}
</style>
