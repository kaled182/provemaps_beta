"""
Pacote de configuração unificado do projeto mapsprovefiber.
Permite importar `settings.dev` ou `settings.prod` conforme o ambiente.
"""

import os
import sys

# -----------------------------------------------------
# Configuração de Ambiente com Validação
# -----------------------------------------------------


def setup_environment():
    """
    Configura o ambiente Django com fallbacks seguros.
    Retorna o nome do módulo de settings a ser usado.
    """
    env_settings = os.getenv("DJANGO_SETTINGS_MODULE", "").strip()

    # Se não especificado, tenta determinar pelo contexto
    if not env_settings:
        if os.getenv("DEBUG", "").lower() == "true":
            env_settings = "settings.dev"
        elif os.getenv("PRODUCTION", "").lower() == "true":
            env_settings = "settings.prod"
        else:
            # Fallback baseado em convenções comuns
            argv = " ".join(sys.argv)
            if "pytest" in argv:
                env_settings = "settings.test"
            elif "runserver" in argv or "shell" in argv:
                env_settings = "settings.dev"
            else:
                env_settings = "settings.dev"  # Default seguro

    # Normaliza o formato
    if env_settings and not env_settings.startswith("settings."):
        env_settings = f"settings.{env_settings}"

    # Valida que o módulo existe (exceto base)
    if env_settings and env_settings != "settings.base":
        try:
            __import__(env_settings)
        except ImportError as e:
            print(f"⚠️  AVISO: Não foi possível importar {env_settings}: {e}")
            print("📁 Usando settings.dev como fallback")
            env_settings = "settings.dev"

    # Define no ambiente
    if env_settings:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", env_settings)

    return env_settings


# Executa a configuração
current_settings = setup_environment()

# -----------------------------------------------------
# Utilitários para Debug
# -----------------------------------------------------


def get_settings_info():
    """Retorna informações sobre as settings atuais para debug."""
    env = "production" if current_settings.endswith(".prod") else (
        "test" if current_settings.endswith(".test") else "development"
    )
    return {
        "module": current_settings,
        "debug": os.getenv("DEBUG", "Not set"),
        "environment": env,
        "python_path": sys.path,
    }


# -----------------------------------------------------
# Importação Condicional para Type Checkers / IDE
# -----------------------------------------------------
# Isso ajuda IDEs e type checkers a entenderem a estrutura (nunca executa em runtime)
if False:  # pragma: no cover
    from .base import *  # type: ignore
    from .dev import *  # type: ignore
    from .prod import *  # type: ignore
