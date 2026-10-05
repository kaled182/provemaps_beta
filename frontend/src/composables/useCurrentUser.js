/**
 * Utilizador autenticado (`/api/users/me/`), pedido uma vez e partilhado.
 * @module useCurrentUser
 */
import { ref, computed } from 'vue';
import { useApi } from '@/composables/useApi';

const user = ref(null);
const loading = ref(false);
let pedido = null;

export function resetCurrentUser() {
  user.value = null;
  pedido = null;
}

export function useCurrentUser() {
  const api = useApi();

  async function load(force = false) {
    if (!force && pedido) return pedido;
    loading.value = true;
    pedido = api
      .get('/api/users/me/')
      .then((data) => {
        user.value = data?.user ?? data ?? null;
        return user.value;
      })
      .catch(() => {
        user.value = null;
        return null;
      })
      .finally(() => {
        loading.value = false;
      });
    return pedido;
  }

  const isStaff = computed(() => Boolean(user.value?.is_staff || user.value?.is_superuser));

  return { user, loading, isStaff, load };
}
