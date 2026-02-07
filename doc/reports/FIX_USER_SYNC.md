# Correção da Sincronização de Usuários → Contatos WhatsApp

## 🐛 Problema Identificado

**Erro HTTP 500** ao clicar no botão "Sincronizar Usuários" na interface.

### Root Cause

A função `sync_contacts_from_users()` em `backend/setup_app/services_contacts.py` estava tentando acessar um campo `phone` diretamente no modelo Django `User`:

```python
# ❌ CÓDIGO INCORRETO (linha 253-254)
users_with_phone = User.objects.exclude(
    models.Q(phone='') | models.Q(phone__isnull=True)  # Campo 'phone' não existe!
).filter(is_active=True)

# ❌ CÓDIGO INCORRETO (linha 265)
phone = ContactImportService._normalize_phone(user.phone)  # AttributeError!
```

**Problema**: O modelo `User` do Django **não possui** campo `phone`. O número de telefone está armazenado em `UserProfile.phone_number` (modelo relacionado 1-to-1).

---

## ✅ Solução Implementada

### Código Corrigido

```python
# ✅ CÓDIGO CORRETO
def sync_contacts_from_users():
    """
    Sincroniza contatos a partir dos usuários do sistema.
    Cria/atualiza contatos para usuários que têm telefone.
    """
    from django.contrib.auth import get_user_model
    from core.models import UserProfile  # ← Importar UserProfile
    
    User = get_user_model()
    
    # ✅ Buscar usuários via relacionamento profile__phone_number
    users_with_phone = User.objects.filter(
        is_active=True,
        profile__phone_number__isnull=False
    ).exclude(
        profile__phone_number=''
    ).select_related('profile')  # ← Otimização (evita N+1 queries)
    
    synced = 0
    errors = []
    
    for user in users_with_phone:
        try:
            # ✅ Pegar telefone do perfil
            profile = user.profile
            if not profile or not profile.phone_number:
                continue
            
            # Tenta encontrar contato existente vinculado ao usuário
            contact = Contact.objects.filter(user=user).first()
            
            if not contact:
                # Tenta encontrar por telefone
                phone = ContactImportService._normalize_phone(profile.phone_number)  # ← profile.phone_number
                contact = Contact.objects.filter(phone=phone).first()
            
            if contact:
                # Atualiza dados
                contact.name = user.get_full_name() or user.username
                contact.email = user.email
                contact.user = user
                contact.save()
            else:
                # Cria novo contato
                Contact.objects.create(
                    name=user.get_full_name() or user.username,
                    phone=ContactImportService._normalize_phone(profile.phone_number),
                    email=user.email,
                    user=user,
                    is_active=True,
                )
            
            synced += 1
            
        except Exception as e:
            errors.append({
                'user_id': user.id,
                'username': user.username,
                'error': str(e)
            })
            logger.error(f"Erro ao sincronizar usuário {user.id}: {e}")
    
    logger.info(f"Sincronização concluída: {synced} usuários sincronizados")
    
    return synced, errors
```

---

## 🧪 Teste Realizado

### Comando Executado

```bash
docker compose -f docker/docker-compose.yml exec web python -c "..."
```

### Resultado do Teste

```
============================================================
TESTE DE SINCRONIZACAO DE USUARIOS
============================================================

Usuario criado: teste_whatsapp
Telefone adicionado: 61999887766

Executando sincronizacao...
INFO: Sincronização concluída: 2 usuários sincronizados
Sincronizados: 2

Contato criado:
  Nome: Teste WhatsApp
  Telefone: +5561999887766  ← Normalizado automaticamente
  Email: teste@whatsapp.com
```

✅ **Sucesso!** 2 usuários sincronizados (admin + teste_whatsapp)

---

## 📊 Estrutura de Dados

### Modelo User (Django Padrão)
```python
# django.contrib.auth.models.User
- username
- email
- first_name
- last_name
- is_active
- is_staff
- is_superuser
# ❌ Não possui campo 'phone'
```

### Modelo UserProfile (core/models.py)
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    phone_number = models.CharField(max_length=20)  # ← CAMPO CORRETO
    telegram_chat_id = models.CharField(max_length=50)
    avatar = models.ImageField(upload_to="avatars/")
    notify_via_email = models.BooleanField(default=True)
    notify_via_whatsapp = models.BooleanField(default=False)
    # ...
```

### Acesso Correto via ORM

```python
# ❌ INCORRETO
user.phone  # AttributeError: 'User' object has no attribute 'phone'

# ✅ CORRETO
user.profile.phone_number  # Acesso via relacionamento 1-to-1

# ✅ QUERY OTIMIZADA
User.objects.filter(
    profile__phone_number__isnull=False
).select_related('profile')
```

---

## 🔄 Processo de Sincronização

1. **Buscar usuários ativos com telefone** (`is_active=True`, `profile__phone_number` preenchido)
2. **Para cada usuário**:
   - Verificar se já existe contato vinculado (`Contact.user == user`)
   - Se não, buscar por telefone normalizado (`Contact.phone == normalized_phone`)
   - Se encontrou, **atualizar** dados (nome, email, user)
   - Se não encontrou, **criar** novo contato
3. **Retornar** contadores de sucesso/erro

---

## 🎯 Próximos Passos

### Testado ✅
- [x] Correção do código
- [x] Restart do container
- [x] Teste via CLI (2 usuários sincronizados)

### Pendente de Teste 🔄
- [ ] Teste via frontend (clicar botão "Sincronizar Usuários")
- [ ] Verificar mensagem de sucesso na interface
- [ ] Confirmar que contatos aparecem na tabela
- [ ] Testar importação CSV/Excel
- [ ] Testar envio de mensagens em massa

---

## 📝 Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `backend/setup_app/services_contacts.py` | Corrigida linha 253-254 (query) e 265 (acesso ao telefone) |
| `docker-web-1` | Reiniciado para aplicar correção |

---

## 🔗 Referências

- **UserProfile Model**: `backend/core/models.py` (linha 8-48)
- **Contact Model**: `backend/setup_app/models_contacts.py` (linha 11-39)
- **Sync Service**: `backend/setup_app/services_contacts.py` (linha 244-298)
- **ViewSet Endpoint**: `backend/setup_app/viewsets_contacts.py` (linha 181-192)
  - URL: `POST /setup_app/api/contacts/sync_from_users/`

---

## 🎉 Status

**🟢 CORRIGIDO** - Endpoint funcionando corretamente, aguardando teste via interface web.
