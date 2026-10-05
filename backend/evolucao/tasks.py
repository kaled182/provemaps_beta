"""Tarefas Celery da Central de Evolução (ADR 0006 §4.6).

Só o aviso dos 14 dias vive aqui. O fecho observado NÃO pode ser tarefa: o contentor não tem
`.git`; essa metade corre no host (`scripts/evolucao_fechados.sh`).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from celery import shared_task  # type: ignore[import-not-found]
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import EvolucaoItem
from .usecases import DIAS_PARADO_PADRAO, itens_parados

logger = logging.getLogger(__name__)

ROTA_CENTRAL = "/system/evolucao"


def destinatarios_staff() -> list[str]:
    """Quem tria: staff ativo com email. Avisar o autor de algo que ele não pode destrancar só o frustra."""
    user_model = get_user_model()
    return sorted(
        {
            e
            for e in user_model.objects.filter(is_staff=True, is_active=True)
            .exclude(email="")
            .values_list("email", flat=True)
            if e
        }
    )


def compor_aviso(parados: list[EvolucaoItem], *, agora: datetime) -> tuple[str, str]:
    """Um email só, com todos os parados: um por item virava ruído diário."""
    linhas = [
        f"- {i.codigo} [{i.estado}] {i.titulo} — parado há {(agora - i.atualizado_em).days} dias"
        for i in parados
    ]
    assunto = f"[ProVeMaps] {len(parados)} item(ns) da Central de Evolução parado(s) há mais de {DIAS_PARADO_PADRAO} dias"
    corpo = (
        "Itens abertos na Central de Evolução sem qualquer toque há mais de "
        f"{DIAS_PARADO_PADRAO} dias:\n\n" + "\n".join(linhas) + f"\n\nTriar em {ROTA_CENTRAL}.\n"
    )
    return assunto, corpo


def avisar_parados(*, agora: datetime | None = None) -> int:
    """Avisa quem tria dos itens a apodrecer; carimba `alerta_parado_em` só DEPOIS de enviar
    (se o envio rebentar, o item continua elegível amanhã). Devolve quantos avisou."""
    agora = agora or timezone.now()
    parados = itens_parados(agora=agora)
    if not parados:
        return 0
    destinatarios = destinatarios_staff()
    if not destinatarios:
        logger.warning("evolucao.parados.sem_destinatarios", extra={"total": len(parados)})
        return 0
    assunto, corpo = compor_aviso(parados, agora=agora)
    send_mail(
        assunto,
        corpo,
        getattr(settings, "DEFAULT_FROM_EMAIL", None) or None,
        destinatarios,
        fail_silently=False,
    )
    EvolucaoItem.objects.filter(pk__in=[i.pk for i in parados]).update(alerta_parado_em=agora)
    return len(parados)


@shared_task(name="evolucao.tasks.avisar_parados_task")
def avisar_parados_task() -> dict[str, Any]:
    try:
        avisados = avisar_parados()
    except Exception as exc:  # a tarefa diária não pode morrer por um SMTP em baixo
        logger.warning("evolucao.parados.falha", extra={"erro": str(exc)[:200]})
        return {"avisados": 0, "erro": str(exc)[:200]}
    logger.info("evolucao.parados.avisados", extra={"total": avisados, "dias": DIAS_PARADO_PADRAO})
    return {"avisados": avisados}
