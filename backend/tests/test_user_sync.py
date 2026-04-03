#!/usr/bin/env python
"""
Script de teste para sincronização de contatos a partir de usuários.
Cria um usuário de teste com telefone e executa a sincronização.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from core.models import UserProfile
from setup_app.services_contacts import sync_contacts_from_users
from setup_app.models_contacts import Contact

User = get_user_model()

print("\n" + "="*60)
print("TESTE DE SINCRONIZAÇÃO DE USUÁRIOS → CONTATOS")
print("="*60 + "\n")

# 1. Criar usuário de teste se não existir
print("[1] Verificando/criando usuário de teste...")
test_username = 'teste_whatsapp'
test_user = User.objects.filter(username=test_username).first()

if not test_user:
    print("   Criando novo usuário...")
    test_user = User.objects.create_user(
        username=test_username,
        email='teste@whatsapp.com',
        password='teste123',
        first_name='Teste',
        last_name='WhatsApp',
        is_active=True
    )
    print(f"   ✅ Usuário criado: {test_user.username}")
else:
    print(f"   ℹ️  Usuário já existe: {test_user.username}")

# 2. Adicionar telefone ao perfil
print("\n[2] Configurando telefone no perfil...")
profile = test_user.profile
if not profile.phone_number:
    profile.phone_number = '61999887766'
    profile.save()
    print(f"   ✅ Telefone adicionado: {profile.phone_number}")
else:
    print(f"   ℹ️  Telefone já configurado: {profile.phone_number}")

# 3. Verificar contatos antes da sincronização
print("\n[3] Verificando contatos antes da sincronização...")
contacts_before = Contact.objects.all().count()
user_contact_before = Contact.objects.filter(user=test_user).first()
print(f"   Total de contatos: {contacts_before}")
if user_contact_before:
    print(f"   ℹ️  Usuário já tem contato: {user_contact_before.name} ({user_contact_before.phone})")
else:
    print(f"   ℹ️  Usuário ainda não tem contato")

# 4. Executar sincronização
print("\n[4] Executando sincronização...")
try:
    synced, errors = sync_contacts_from_users()
    print(f"   ✅ Sincronização concluída!")
    print(f"   Usuários sincronizados: {synced}")
    if errors:
        print(f"   ⚠️  Erros encontrados: {len(errors)}")
        for err in errors:
            print(f"      - User {err['username']}: {err['error']}")
except Exception as e:
    print(f"   ❌ Erro na sincronização: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Verificar contatos depois da sincronização
print("\n[5] Verificando contatos depois da sincronização...")
contacts_after = Contact.objects.all().count()
user_contact_after = Contact.objects.filter(user=test_user).first()
print(f"   Total de contatos: {contacts_after}")

if user_contact_after:
    print(f"   ✅ Contato criado/atualizado:")
    print(f"      Nome: {user_contact_after.name}")
    print(f"      Telefone: {user_contact_after.phone}")
    print(f"      Email: {user_contact_after.email}")
    print(f"      User: {user_contact_after.user.username if user_contact_after.user else 'N/A'}")
    print(f"      Ativo: {user_contact_after.is_active}")
else:
    print(f"   ⚠️  Nenhum contato encontrado para o usuário!")

# 6. Estatísticas finais
print("\n" + "="*60)
print("RESULTADO")
print("="*60)
print(f"✅ Usuários ativos com telefone: {User.objects.filter(is_active=True, profile__phone_number__isnull=False).exclude(profile__phone_number='').count()}")
print(f"✅ Total de contatos: {Contact.objects.count()}")
print(f"✅ Contatos vinculados a usuários: {Contact.objects.filter(user__isnull=False).count()}")
print("="*60 + "\n")
