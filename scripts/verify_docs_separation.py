#!/usr/bin/env python3
"""Verify content separation between REFATORAR.md and FUTURE_APPS.md"""

import re

ref_path = r'd:\provemaps_beta\doc\developer\REFATORAR.md'
fut_path = r'd:\provemaps_beta\doc\developer\FUTURE_APPS.md'

with open(ref_path, 'r', encoding='utf-8') as f:
    ref = f.read()

with open(fut_path, 'r', encoding='utf-8') as f:
    fut = f.read()

print('='*80)
print('REFATORAR.md (Current State - Phases 0-5 Complete)')
print('='*80)
print(f'  ✓ Total lines: {len(ref.splitlines())}')
print(f'  ✓ Contains "Matriz de Recursos": {bool(re.search(r"Matriz de Recursos", ref))}')
print(f'  ✓ Contains "Edições Planejadas": {bool(re.search(r"Edições Planejadas", ref))}')
print(f'  ✓ References FUTURE_APPS.md: {ref.count("FUTURE_APPS.md")} times')
print(f'  ✓ Contains Fase 5 progress: {"Progresso Fase 5" in ref}')
print(f'  ✓ Contains deployment playbook: {"Playbook de Deploy" in ref}')

print()
print('='*80)
print('FUTURE_APPS.md (Roadmap - Phases 6-15 Planned)')
print('='*80)
print(f'  ✓ Total lines: {len(fut.splitlines())}')
print(f'  ✓ Contains "Matriz de Recursos": {bool(re.search(r"Matriz de Recursos", fut))}')
print(f'  ✓ Contains "Edições Planejadas": {bool(re.search(r"Edições Planejadas", fut))}')
print(f'  ✓ Contains RCA section: {"Root Cause Analysis" in fut}')
print(f'  ✓ Contains GPON section: {bool(re.search(r"GPON", fut))}')
print(f'  ✓ Contains DWDM section: {bool(re.search(r"DWDM", fut))}')
print(f'  ✓ Contains catálogos: {"FiberSpec" in fut or "CableSpec" in fut}')
print(f'  ✓ Contains decisões arquiteturais: {"Decisões Arquiteturais" in fut or "PostGIS" in fut}')
print(f'  ✓ Contains roadmap: {"Roadmap" in fut or "Fases 6" in fut}')

print()
print('='*80)
print('Validation Summary')
print('='*80)

# Check no future content in REFATORAR
has_rca_details = "Motor de Correlação de Eventos" in ref
has_gpon_details = "Auto-Provisionamento (ZTP" in ref and "Fluxo:" in ref
has_dwdm_details = "Planejador de Orçamento Óptico" in ref

print(f'  ✓ REFATORAR.md has detailed RCA specs: {has_rca_details}')
print(f'  ✓ REFATORAR.md has detailed GPON specs: {has_gpon_details}')
print(f'  ✓ REFATORAR.md has detailed DWDM specs: {has_dwdm_details}')

if has_rca_details or has_gpon_details or has_dwdm_details:
    print()
    print('  ⚠️  WARNING: REFATORAR.md still contains future content!')
    print('     Expected: Only current state (Phases 0-5)')
    print('     Found: Detailed future specifications')
else:
    print()
    print('  ✅ SUCCESS: Content properly separated!')
    print('     - REFATORAR.md: Current state only (Phases 0-5)')
    print('     - FUTURE_APPS.md: Future roadmap (Phases 6-15)')

print('='*80)
