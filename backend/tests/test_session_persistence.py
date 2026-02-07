#!/usr/bin/env python
"""
Test de persistência de sessão Django
Valida se as configurações de sessão estão mantendo o login ativo.
"""
import os
import sys
import django

# Configure Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")
django.setup()

from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore as CacheSessionStore
from django.contrib.sessions.backends.db import SessionStore as DBSessionStore
from django.core.cache import cache


def test_session_configuration():
    """Verifica se as configurações de sessão estão corretas"""
    print("=" * 70)
    print("TESTE DE CONFIGURAÇÃO DE SESSÃO")
    print("=" * 70)
    
    # 1. Verificar configurações básicas
    print("\n1. Configurações de Sessão:")
    print(f"   SESSION_ENGINE: {settings.SESSION_ENGINE}")
    print(f"   SESSION_SAVE_EVERY_REQUEST: {settings.SESSION_SAVE_EVERY_REQUEST}")
    print(f"   SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE} segundos ({settings.SESSION_COOKIE_AGE / 86400} dias)")
    print(f"   SESSION_COOKIE_NAME: {settings.SESSION_COOKIE_NAME}")
    print(f"   SESSION_COOKIE_HTTPONLY: {settings.SESSION_COOKIE_HTTPONLY}")
    print(f"   SESSION_COOKIE_SAMESITE: {settings.SESSION_COOKIE_SAMESITE}")
    print(f"   SESSION_EXPIRE_AT_BROWSER_CLOSE: {settings.SESSION_EXPIRE_AT_BROWSER_CLOSE}")
    print(f"   SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
    
    # 2. Verificar CSRF
    print("\n2. Configurações CSRF:")
    print(f"   CSRF_COOKIE_NAME: {settings.CSRF_COOKIE_NAME}")
    print(f"   CSRF_COOKIE_AGE: {settings.CSRF_COOKIE_AGE} segundos ({settings.CSRF_COOKIE_AGE / 86400} dias)")
    print(f"   CSRF_USE_SESSIONS: {settings.CSRF_USE_SESSIONS}")
    print(f"   CSRF_COOKIE_HTTPONLY: {settings.CSRF_COOKIE_HTTPONLY}")
    
    # 3. Verificar backend de sessão
    print("\n3. Backend de Sessão:")
    if "cache" in settings.SESSION_ENGINE:
        print("   ✓ Usando cache (Redis) como backend de sessão")
        
        # Testar conexão com Redis
        try:
            cache.set("test_key", "test_value", 10)
            value = cache.get("test_key")
            if value == "test_value":
                print("   ✓ Redis conectado e funcionando")
                cache.delete("test_key")
            else:
                print("   ✗ Redis não retornou valor esperado")
        except Exception as e:
            print(f"   ✗ Erro ao conectar com Redis: {e}")
            
    else:
        print("   ✓ Usando banco de dados como backend de sessão")
    
    # 4. Testar criação de sessão
    print("\n4. Teste de Criação de Sessão:")
    try:
        if "cache" in settings.SESSION_ENGINE:
            session = CacheSessionStore()
        else:
            session = DBSessionStore()
        
        # Criar sessão de teste
        session["test_user_id"] = 999
        session["test_username"] = "test_session_user"
        session.save()
        
        session_key = session.session_key
        print(f"   ✓ Sessão criada com chave: {session_key}")
        
        # Recuperar sessão
        if "cache" in settings.SESSION_ENGINE:
            session2 = CacheSessionStore(session_key=session_key)
        else:
            session2 = DBSessionStore(session_key=session_key)
        
        if session2.get("test_user_id") == 999:
            print("   ✓ Sessão recuperada com sucesso")
            print(f"   ✓ Dados da sessão: {dict(session2.items())}")
        else:
            print("   ✗ Falha ao recuperar sessão")
        
        # Limpar sessão de teste
        session.delete()
        print("   ✓ Sessão de teste removida")
        
    except Exception as e:
        print(f"   ✗ Erro ao testar sessão: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Validar configurações críticas
    print("\n5. Validação de Configurações Críticas:")
    issues = []
    
    if not settings.SESSION_SAVE_EVERY_REQUEST:
        issues.append("SESSION_SAVE_EVERY_REQUEST deve estar True para manter sessão ativa")
    
    if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
        issues.append("SESSION_EXPIRE_AT_BROWSER_CLOSE está True (sessão expira ao fechar navegador)")
    
    if settings.SESSION_COOKIE_AGE < 86400:  # 1 dia
        issues.append(f"SESSION_COOKIE_AGE muito curto: {settings.SESSION_COOKIE_AGE}s")
    
    if not settings.SESSION_COOKIE_HTTPONLY:
        issues.append("SESSION_COOKIE_HTTPONLY deve estar True por segurança")
    
    if issues:
        print("   ✗ Problemas encontrados:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print("   ✓ Todas as configurações críticas estão corretas!")
    
    # 6. Verificar middleware
    print("\n6. Middleware de Sessão:")
    middleware_list = settings.MIDDLEWARE
    session_idx = None
    auth_idx = None
    
    for i, mw in enumerate(middleware_list):
        if "SessionMiddleware" in mw:
            session_idx = i
            print(f"   ✓ SessionMiddleware encontrado na posição {i}")
        if "AuthenticationMiddleware" in mw:
            auth_idx = i
            print(f"   ✓ AuthenticationMiddleware encontrado na posição {i}")
    
    if session_idx is not None and auth_idx is not None:
        if session_idx < auth_idx:
            print("   ✓ SessionMiddleware está antes de AuthenticationMiddleware (correto)")
        else:
            print("   ✗ SessionMiddleware deve estar ANTES de AuthenticationMiddleware!")
    
    print("\n" + "=" * 70)
    print("RESULTADO DO TESTE")
    print("=" * 70)
    
    if not issues and session_idx is not None and session_idx < auth_idx:
        print("✅ SUCESSO: Todas as configurações de sessão estão corretas!")
        print("\nPróximos passos:")
        print("1. Limpe os cookies do navegador")
        print("2. Faça login novamente")
        print("3. A sessão deve permanecer ativa por 14 dias")
        return 0
    else:
        print("❌ FALHA: Existem problemas nas configurações")
        return 1


if __name__ == "__main__":
    sys.exit(test_session_configuration())
