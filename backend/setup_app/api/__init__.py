"""Views HTTP do setup_app, um módulo por domínio (EV-0017).

Cada view: decoradores de acesso, parsing do pedido, chamada ao usecase,
tradução de exceções em códigos HTTP e registo em `ConfigurationAudit`.
"""
