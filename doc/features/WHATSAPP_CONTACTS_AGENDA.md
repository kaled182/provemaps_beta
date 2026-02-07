# Sistema de Agenda de Contatos WhatsApp - Guia de Implementação

## ✅ Concluído

### Backend
- ✅ **Models** criados em `backend/setup_app/models_contacts.py`:
  - `Contact`: Contatos com nome, telefone, email, empresa, cargo, notas
  - `ContactGroup`: Grupos de contatos (Clientes, Fornecedores, etc)
  - `ImportHistory`: Histórico de importações CSV/Excel
  
- ✅ **Serializers** criados em `backend/setup_app/serializers_contacts.py`:
  - `ContactSerializer`: CRUD de contatos
  - `ContactGroupSerializer`: CRUD de grupos
  - `ImportHistorySerializer`: Visualização de histórico
  - `ContactImportSerializer`: Upload de arquivos
  - `BulkMessageSerializer`: Envio em massa

- ✅ **Service** criado em `backend/setup_app/services_contacts.py`:
  - `ContactImportService`: Importa CSV/Excel, normaliza telefones
  - `sync_contacts_from_users()`: Sincroniza usuários do sistema

- ✅ **Migrations** aplicadas: `0022_add_contacts_models`

---

## 🚧 Próximos Passos

### 1. Criar ViewSets da API

Criar arquivo `backend/setup_app/viewsets_contacts.py`:

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models_contacts import Contact, ContactGroup, ImportHistory
from .serializers_contacts import (
    ContactSerializer,
    ContactListSerializer,
    ContactGroupSerializer,
    ImportHistorySerializer,
    ContactImportSerializer,
    BulkMessageSerializer,
)
from .services_contacts import ContactImportService, sync_contacts_from_users


class ContactGroupViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de grupos de contatos"""
    queryset = ContactGroup.objects.all()
    serializer_class = ContactGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de contatos"""
    queryset = Contact.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'groups']
    search_fields = ['name', 'phone', 'email', 'company']
    ordering_fields = ['name', 'created_at', 'message_count']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    def get_queryset(self):
        queryset = Contact.objects.all()
        
        # Filtro por grupo
        group_id = self.request.query_params.get('group_id')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
        
        # Filtro por ativo
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def import_file(self, request):
        """Importa contatos de arquivo CSV ou Excel"""
        serializer = ContactImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        group_id = serializer.validated_data.get('group_id')
        update_existing = serializer.validated_data.get('update_existing', False)
        
        # Executa importação
        service = ContactImportService(
            user=request.user,
            group_id=group_id,
            update_existing=update_existing
        )
        import_history = service.import_from_file(file)
        
        # Retorna resultado
        return Response({
            'success': import_history.status == 'completed',
            'message': f'Importação concluída: {import_history.successful_imports} sucesso, {import_history.failed_imports} falhas',
            'import_history': ImportHistorySerializer(import_history).data
        })
    
    @action(detail=False, methods=['post'])
    def sync_from_users(self, request):
        """Sincroniza contatos a partir dos usuários do sistema"""
        synced, errors = sync_contacts_from_users()
        
        return Response({
            'success': True,
            'message': f'{synced} usuários sincronizados',
            'synced_count': synced,
            'errors': errors
        })
    
    @action(detail=False, methods=['post'])
    def bulk_message(self, request):
        """Envia mensagem para múltiplos contatos"""
        serializer = BulkMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # TODO: Implementar envio em massa via Celery task
        # Ver: backend/setup_app/tasks.py
        
        return Response({
            'success': True,
            'message': 'Mensagens agendadas para envio'
        })


class ImportHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet somente leitura para histórico de importações"""
    queryset = ImportHistory.objects.all()
    serializer_class = ImportHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'filename']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Apenas importações do usuário atual (ou todos se staff)
        queryset = ImportHistory.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(imported_by=self.request.user)
        return queryset
```

### 2. Adicionar URLs

Editar `backend/setup_app/urls.py` e adicionar:

```python
from .viewsets_contacts import ContactViewSet, ContactGroupViewSet, ImportHistoryViewSet

router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'contact-groups', ContactGroupViewSet, basename='contact-group')
router.register(r'contact-imports', ImportHistoryViewSet, basename='contact-import')
```

### 3. Instalar dependência openpyxl

Adicionar ao `backend/requirements.txt`:
```
openpyxl==3.1.2  # Para leitura de arquivos Excel
```

Rodar:
```bash
docker compose -f docker/docker-compose.yml exec web pip install openpyxl
```

---

## 🎨 Frontend

### Componentes a criar em `frontend/src/components/Configuration/`:

1. **ContactsTab.vue** - Aba principal com lista de contatos
2. **ContactList.vue** - Lista de contatos (similar a WhatsAppGatewayList)
3. **ContactEditModal.vue** - Modal para adicionar/editar contato
4. **ContactImportModal.vue** - Modal para upload de CSV/Excel
5. **ContactGroupManager.vue** - Gerenciamento de grupos
6. **BulkMessageModal.vue** - Modal para envio em massa

### Estrutura ContactsTab.vue:

```vue
<template>
  <div class="contacts-tab">
    <!-- Toolbar -->
    <div class="toolbar">
      <button @click="showAddModal = true">
        Adicionar Contato
      </button>
      <button @click="showImportModal = true">
        Importar CSV/Excel
      </button>
      <button @click="syncFromUsers">
        Sincronizar Usuários
      </button>
      <button @click="showBulkMessageModal = true">
        Enviar Mensagens em Massa
      </button>
    </div>

    <!-- Filtros -->
    <div class="filters">
      <input v-model="search" placeholder="Buscar contatos..." />
      <select v-model="filterGroup">
        <option value="">Todos os grupos</option>
        <option v-for="group in groups" :key="group.id" :value="group.id">
          {{ group.name }}
        </option>
      </select>
      <label>
        <input type="checkbox" v-model="showOnlyActive" />
        Apenas ativos
      </label>
    </div>

    <!-- Lista de Contatos -->
    <ContactList 
      :contacts="filteredContacts"
      @edit="handleEdit"
      @delete="handleDelete"
      @send-message="handleSendMessage"
    />

    <!-- Modals -->
    <ContactEditModal
      v-if="showEditModal"
      :contact="editingContact"
      :groups="groups"
      @close="showEditModal = false"
      @save="handleSave"
    />

    <ContactImportModal
      v-if="showImportModal"
      :groups="groups"
      @close="showImportModal = false"
      @import="handleImport"
    />

    <BulkMessageModal
      v-if="showBulkMessageModal"
      :selected-contacts="selectedContacts"
      :gateways="whatsappGateways"
      @close="showBulkMessageModal = false"
      @send="handleBulkSend"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useContactsStore } from '@/stores/contacts'
import ContactList from './ContactList.vue'
import ContactEditModal from './ContactEditModal.vue'
import ContactImportModal from './ContactImportModal.vue'
import BulkMessageModal from './BulkMessageModal.vue'

const contactsStore = useContactsStore()

const search = ref('')
const filterGroup = ref('')
const showOnlyActive = ref(true)
const showAddModal = ref(false)
const showEditModal = ref(false)
const showImportModal = ref(false)
const showBulkMessageModal = ref(false)
const editingContact = ref(null)
const selectedContacts = ref([])

const filteredContacts = computed(() => {
  let filtered = contactsStore.contacts
  
  if (search.value) {
    filtered = filtered.filter(c => 
      c.name.toLowerCase().includes(search.value.toLowerCase()) ||
      c.phone.includes(search.value)
    )
  }
  
  if (filterGroup.value) {
    filtered = filtered.filter(c => 
      c.groups.some(g => g.id === filterGroup.value)
    )
  }
  
  if (showOnlyActive.value) {
    filtered = filtered.filter(c => c.is_active)
  }
  
  return filtered
})

onMounted(() => {
  contactsStore.loadContacts()
  contactsStore.loadGroups()
})

// Handlers...
</script>
```

### Pinia Store (`frontend/src/stores/contacts.js`):

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

export const useContactsStore = defineStore('contacts', () => {
  const api = useApi()
  const notify = useNotification()
  
  const contacts = ref([])
  const groups = ref([])
  const importHistory = ref([])
  const loading = ref(false)
  
  const loadContacts = async () => {
    loading.value = true
    try {
      const res = await api.get('/setup_app/api/contacts/')
      if (res.success) {
        contacts.value = res.contacts || []
      }
    } catch (error) {
      notify.error('Erro', 'Falha ao carregar contatos')
    } finally {
      loading.value = false
    }
  }
  
  const loadGroups = async () => {
    try {
      const res = await api.get('/setup_app/api/contact-groups/')
      if (res.success) {
        groups.value = res.groups || []
      }
    } catch (error) {
      notify.error('Erro', 'Falha ao carregar grupos')
    }
  }
  
  const saveContact = async (contactData) => {
    try {
      const url = contactData.id 
        ? `/setup_app/api/contacts/${contactData.id}/`
        : '/setup_app/api/contacts/'
      
      const res = contactData.id
        ? await api.put(url, contactData)
        : await api.post(url, contactData)
      
      if (res.success) {
        notify.success('Sucesso', 'Contato salvo')
        await loadContacts()
        return true
      }
    } catch (error) {
      notify.error('Erro', 'Falha ao salvar contato')
      return false
    }
  }
  
  const importContacts = async (file, groupId, updateExisting) => {
    const formData = new FormData()
    formData.append('file', file)
    if (groupId) formData.append('group_id', groupId)
    formData.append('update_existing', updateExisting)
    
    try {
      const res = await api.post('/setup_app/api/contacts/import_file/', formData)
      if (res.success) {
        notify.success('Importação', res.message)
        await loadContacts()
        return res.import_history
      }
    } catch (error) {
      notify.error('Erro', 'Falha na importação')
      return null
    }
  }
  
  const syncFromUsers = async () => {
    try {
      const res = await api.post('/setup_app/api/contacts/sync_from_users/')
      if (res.success) {
        notify.success('Sincronização', res.message)
        await loadContacts()
      }
    } catch (error) {
      notify.error('Erro', 'Falha ao sincronizar')
    }
  }
  
  const deleteContact = async (contactId) => {
    try {
      const res = await api.delete(`/setup_app/api/contacts/${contactId}/`)
      if (res.success) {
        notify.success('Sucesso', 'Contato excluído')
        await loadContacts()
        return true
      }
    } catch (error) {
      notify.error('Erro', 'Falha ao excluir')
      return false
    }
  }
  
  return {
    contacts,
    groups,
    importHistory,
    loading,
    loadContacts,
    loadGroups,
    saveContact,
    importContacts,
    syncFromUsers,
    deleteContact,
  }
})
```

---

## 📋 Checklist de Implementação

### Backend
- [x] Models criados
- [x] Serializers criados
- [x] Service de importação criado
- [x] Migrations aplicadas
- [ ] ViewSets criados
- [ ] URLs registradas
- [ ] openpyxl instalado
- [ ] Testes criados

### Frontend
- [ ] Pinia store criada
- [ ] ContactsTab.vue
- [ ] ContactList.vue
- [ ] ContactEditModal.vue
- [ ] ContactImportModal.vue
- [ ] ContactGroupManager.vue
- [ ] BulkMessageModal.vue
- [ ] Integrado em GatewaysTab.vue
- [ ] Testes E2E

### Funcionalidades
- [ ] CRUD de contatos
- [ ] CRUD de grupos
- [ ] Importação CSV
- [ ] Importação Excel
- [ ] Sincronização com usuários
- [ ] Envio de mensagens individuais
- [ ] Envio em massa
- [ ] Histórico de importações
- [ ] Filtros e busca

---

## 🔧 Comandos Úteis

```bash
# Criar migrations
docker compose -f docker/docker-compose.yml exec web python manage.py makemigrations

# Aplicar migrations
docker compose -f docker/docker-compose.yml exec web python manage.py migrate

# Instalar openpyxl
docker compose -f docker/docker-compose.yml exec web pip install openpyxl

# Rebuild container (se alterar requirements.txt)
docker compose -f docker/docker-compose.yml build web

# Ver logs
docker compose -f docker/docker-compose.yml logs -f web

# Shell Django
docker compose -f docker/docker-compose.yml exec web python manage.py shell
```

---

## 📊 Exemplo de CSV para Importação

```csv
name,phone,email,company,position,notes
João Silva,+5561999999999,joao@example.com,Empresa A,Gerente,Cliente VIP
Maria Santos,61988888888,maria@example.com,Empresa B,Diretora,
Pedro Oliveira,+55 61 97777-7777,pedro@example.com,,Freelancer,Contato técnico
```

**Campos aceitos (case-insensitive):**
- `name` ou `nome` (obrigatório)
- `phone`, `telefone` ou `celular` (obrigatório)
- `email` ou `e-mail`
- `company` ou `empresa`
- `position` ou `cargo`
- `notes`, `observacoes` ou `obs`

---

## 🎯 Próxima Sessão

**Para continuar o desenvolvimento:**

1. Criar `viewsets_contacts.py` conforme exemplo acima
2. Registrar URLs
3. Testar endpoints com Postman/Thunder Client
4. Criar store Pinia
5. Criar componentes Vue incrementalmente
6. Integrar na aba WhatsApp

**Endpoint de teste rápido:**
```bash
curl -X POST http://localhost:8000/setup_app/api/contacts/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Teste","phone":"+5561999999999","email":"teste@example.com"}'
```
