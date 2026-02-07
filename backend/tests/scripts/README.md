# 📝 Scripts de Teste e Debug

Esta pasta contém scripts utilitários para diagnóstico, verificação e correção de dados.

## 📂 Conteúdo

### Verificação de Dados

- **check_cables.py** — Verifica integridade de cabos de fibra
- **check_cameras.py** — Verifica configuração de câmeras
- **check_furacao_devices.py** — Verifica dispositivos em Furacao
- **check_index.py** — Verifica índices do banco de dados
- **check_planaltina_distance.py** — Verifica cálculos de distância

### Diagnóstico

- **diagnose_zabbix.py** — Diagnóstico de integração Zabbix
- **verify_gist_index.py** — Verifica índices GIST PostGIS

### Correção de Dados

- **fix_cable_50.py** — Corrige dados do cabo 50
- **fix_existing_cable_segments.py** — Corrige segmentos de cabos
- **fix_split_ceo_9384.py** — Corrige split CEO 9384

### Testes Manuais

- **test_fusion_manual.py** — Teste manual de fusões
- **test_optical_integration.py** — Teste de integração óptica
- **test_split_v2.py** — Teste de splits v2
- **test_zabbix_api_direct.py** — Teste direto de API Zabbix
- **test_zabbix_integration.py** — Teste de integração Zabbix

## 🚀 Execução

**IMPORTANTE**: Sempre executar via Docker

```bash
# Executar script de verificação
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/check_cables.py

# Executar script de diagnóstico
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/diagnose_zabbix.py

# Executar teste manual
docker compose -f docker/docker-compose.yml exec web python backend/tests/scripts/test_fusion_manual.py
```

## ⚠️ Avisos

- **Não execute diretamente no host** — Use Docker sempre
- **Scripts fix_* modificam dados** — Faça backup antes de executar
- **Scripts de teste não são pytest** — Executar com `python`, não `pytest`

## 📚 Documentação

Para testes automatizados, consulte:
- [doc/testing/README.md](../../../doc/testing/README.md)
- [doc/testing/TESTING_GUIDE.md](../../../doc/testing/TESTING_GUIDE.md)
