# MapsProveFiber — Documentação

## Visão Geral

**MapsProveFiber** é uma plataforma Django para gerenciamento de redes de fibra óptica, integração com Zabbix e visualização de mapas interativos.

## Recursos Principais

- 🗺️ **Visualização de Mapas** — Interfaces interativas com Google Maps
- 📊 **Monitoramento Zabbix** — Integração nativa com API Zabbix
- 🛣️ **Construtor de Rotas** — Planejamento e documentação de rotas de fibra
- ⚙️ **Setup Simplificado** — Configuração via interface web
- 📈 **Métricas Prometheus** — Observabilidade completa

## Quick Start

```bash
# Clone o repositório
git clone https://github.com/kaled182/mapsprovefiber.git
cd mapsprovefiber

# Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Execute migrações
python manage.py migrate

# Inicie servidor
python manage.py runserver
```

## Estrutura do Projeto

```
mapsprovefiber/
├── core/              # Configurações Django e URLs raiz
├── maps_view/         # Visualização de mapas e dashboard
├── routes_builder/    # Construtor de rotas de fibra
├── setup_app/         # Interface de configuração
├── zabbix_api/        # Integração com Zabbix
├── docs/              # Documentação markdown
└── tests/             # Testes automatizados
```

## Documentação Adicional

- [API Documentation](API_DOCUMENTATION.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Contributing Guidelines](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## Suporte

Para questões e suporte:
- **Issues:** [GitHub Issues](https://github.com/kaled182/mapsprovefiber/issues)
- **Discussões:** [GitHub Discussions](https://github.com/kaled182/mapsprovefiber/discussions)

---
**Versão:** 1.0.0 | **Licença:** MIT
