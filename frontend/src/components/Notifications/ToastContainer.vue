<template>
  <div class="fixed top-4 right-4 z-[2500] space-y-2 max-w-sm">
    <transition-group name="toast">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="[
          'rounded-lg shadow-lg p-4 flex items-start space-x-3',
          'transform transition-all duration-300 ease-in-out',
          typeClasses[notification.type]
        ]"
      >
        <div class="flex-shrink-0">
          <i :class="iconClasses[notification.type]" class="text-xl"></i>
        </div>
        <div class="flex-1 pt-0.5">
          <p class="font-semibold text-sm">{{ notification.title }}</p>
          <p v-if="notification.message" class="text-sm mt-1 opacity-90">
            {{ notification.message }}
          </p>
        </div>
        <button
          @click="remove(notification.id)"
          class="flex-shrink-0 text-current opacity-70 hover:opacity-100 transition-opacity"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useNotification } from '@/composables/useNotification';

const { notifications, remove } = useNotification();

const typeClasses = {
  success: 'bg-green-500 text-white',
  error: 'bg-red-500 text-white',
  warning: 'bg-yellow-500 text-white',
  info: 'bg-blue-500 text-white',
};

const iconClasses = {
  success: 'fas fa-check-circle',
  error: 'fas fa-exclamation-circle',
  warning: 'fas fa-exclamation-triangle',
  info: 'fas fa-info-circle',
};
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px) scale(0.95);
}
</style>
