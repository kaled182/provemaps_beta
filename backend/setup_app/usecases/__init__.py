"""Usecases do setup_app (EV-0017).

Lógica de negócio sem HttpRequest/JsonResponse: recebe valores simples, devolve
dicts/paths e levanta exceções de domínio. As views em `setup_app/api/` ficam
finas: autenticação, parsing, códigos HTTP e auditoria.
"""
