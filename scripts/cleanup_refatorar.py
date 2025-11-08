#!/usr/bin/env python3
"""
Removes future planning content from REFATORAR.md and replaces with reference to FUTURE_APPS.md
"""

def main():
    refatorar_path = r'd:\provemaps_beta\doc\developer\REFATORAR.md'
    
    with open(refatorar_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Find start: line with "## 🗺️ Matriz de Recursos (alto nível)"
    start_idx = None
    for i, line in enumerate(lines):
        if '## 🗺️ Matriz de Recursos (alto nível)' in line:
            start_idx = i
            break
    
    # Find end: line with "# 🔧 Plano de Modularização do Backend"
    end_idx = None
    if start_idx is not None:
        for i in range(start_idx, len(lines)):
            if '# 🔧 Plano de Modularização do Backend' in lines[i]:
                end_idx = i
                break
    
    if start_idx is None or end_idx is None:
        print(f"ERROR: Could not find markers. start_idx={start_idx}, end_idx={end_idx}")
        return
    
    # Replacement text
    replacement = """
---

> **📋 Nota Importante:** A matriz completa de recursos, especificações técnicas detalhadas das 4 edições (MONITORAMENTO, +Mapeamento, +GPON, +DWDM), catálogos de referência, decisões arquiteturais, questões em aberto e roadmap de implementação (Fases 6-15) foram movidos para **[`FUTURE_APPS.md`](./FUTURE_APPS.md)**.

---

# 🔧 Plano de Modularização do Backend"""
    
    # Rebuild file
    new_lines = lines[:start_idx] + [replacement] + lines[end_idx+1:]
    
    with open(refatorar_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ Successfully removed {end_idx - start_idx} lines (lines {start_idx+1}-{end_idx+1})")
    print(f"   Replaced with reference to FUTURE_APPS.md")
    print(f"   New file has {len(new_lines)} lines (was {len(lines)} lines)")

if __name__ == '__main__':
    main()
