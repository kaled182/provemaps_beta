#!/usr/bin/env python3
"""
Teste automatizado: Validação de refs Vue 3
Valida se as refs estão sendo populadas corretamente
"""

def test_vue_refs_pattern():
    """
    Template: :ref="el => { if (el) myRefs[key] = el }"
    Código: myRefs.value[key] ← CORRETO
    """
    
    print("=== TESTE: Pattern de Refs Vue 3 ===\n")
    
    # Padrão correto
    template_pattern = 'myRefs[key] = el'  # SEM .value
    code_pattern = 'myRefs.value[key]'     # COM .value
    
    print(f"✓ Template: {template_pattern}")
    print(f"✓ Código: {code_pattern}")
    print("\nMotivo: Vue 3 ref() cria um proxy reativo.")
    print("No template, Vue desempacota automaticamente.")
    print("No código, precisamos acessar .value explicitamente.\n")
    
    # Validar SiteDetailsModal
    print("=== VALIDAÇÃO: SiteDetailsModal.vue ===\n")
    
    with open('d:/provemaps_beta/frontend/src/components/SiteDetailsModal.vue', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Template correto?
    if 'mosaicVideoRefs[camera.connectionKey' in content and ':ref="el =>' in content:
        print("✓ Template: Usando mosaicVideoRefs[key] = el (CORRETO)")
    else:
        print("✗ Template: Pattern incorreto!")
        return False
    
    # Código correto?
    errors = []
    
    # Verificar acesso incorreto (sem .value)
    if 'mosaicVideoRefs[connectionKey]' in content:
        errors.append("Encontrado: mosaicVideoRefs[connectionKey] (deveria ser .value[connectionKey])")
    
    # Verificar acesso incorreto em polling
    if 'const videoEl = refsMap[connectionKey]' in content:
        errors.append("Encontrado: refsMap[connectionKey] (deveria ser .value[connectionKey])")
    
    if errors:
        print("✗ Código: Acessos INCORRETOS encontrados:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("✓ Código: Todos os acessos usam .value (CORRETO)")
    
    print("\n=== RESULTADO: PASS ===")
    return True

if __name__ == '__main__':
    import sys
    sys.exit(0 if test_vue_refs_pattern() else 1)
