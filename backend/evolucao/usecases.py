"""Regras da Central de Evolução (ADR 0006): dicts para fora, exceções de domínio para erros."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.db.models import F, Q, QuerySet
from django.utils import timezone

from .models import ESTADOS_ABERTOS, EvolucaoAnexo, EvolucaoContador, EvolucaoItem

#: 14 dias. Tempo de sobra para triar sem virar ruído semanal; o aviso é só para quem tria.
DIAS_PARADO_PADRAO = 14

#: «O campo não veio no pedido», distinto de «veio a null». Só a prioridade precisa dela:
#: é o único campo cujo vazio é um valor de domínio («por triar»).
NAO_MEXER: Any = object()


class EvolucaoError(ValueError):
    status = 400


class ItemNaoEncontrado(EvolucaoError):
    status = 404


class SemPermissaoTriar(EvolucaoError):
    status = 403


def pode_triar(user) -> bool:
    return bool(getattr(user, "is_staff", False))


def proximo_codigo() -> str:
    return f"EV-{EvolucaoContador.proximo():04d}"


def serialize_anexo(anexo: EvolucaoAnexo) -> dict[str, Any]:
    return {
        "id": anexo.id,
        "nome_original": anexo.nome_original,
        "content_type": anexo.content_type,
        "tamanho": anexo.tamanho,
    }


def serialize_item(item: EvolucaoItem, anexos: list[EvolucaoAnexo] | None = None) -> dict[str, Any]:
    """Chaves na ordem da resposta (o serializer DRF espelha-as sem reordenar)."""
    if anexos is None:
        anexos = list(item.anexos.all())
    return {
        "id": item.id,
        "codigo": item.codigo,
        "tipo": item.tipo,
        "titulo": item.titulo,
        "descricao": item.descricao,
        "estado": item.estado,
        "recusa_motivo": item.recusa_motivo or None,
        "impacto": item.impacto or None,
        "prioridade": item.prioridade,
        "etiquetas": list(item.etiquetas or []),
        "origem": item.origem,
        "autor": item.autor.get_username() if item.autor_id and item.autor else None,
        "contexto": dict(item.contexto or {}),
        "evidencia": item.evidencia,
        "fechado_por": item.fechado_por,
        "anexos": [serialize_anexo(a) for a in anexos],
        "criado_em": item.criado_em.isoformat(),
        "atualizado_em": item.atualizado_em.isoformat(),
    }


@transaction.atomic
def criar_item(
    *,
    autor,
    tipo: str,
    titulo: str,
    descricao: str,
    impacto: str = "",
    contexto: dict[str, Any] | None = None,
    origem: str = "humano",
    evidencia: dict[str, Any] | None = None,
    anexos: list[int] | None = None,
) -> EvolucaoItem:
    """Nasce em `entrada`, sem prioridade — ainda ninguém olhou. O autor vem da sessão."""
    if origem == "agente" and not evidencia:
        raise EvolucaoError("Um item do agente exige evidência (ficheiro, linha, comando).")
    item = EvolucaoItem.objects.create(
        codigo=proximo_codigo(),
        tipo=tipo,
        titulo=titulo.strip(),
        descricao=descricao.strip(),
        impacto=impacto or "",
        autor=autor if getattr(autor, "pk", None) else None,
        contexto=contexto or {},
        origem=origem,
        evidencia=evidencia if origem == "agente" else (evidencia or None),
    )
    if anexos:
        # Anexos carregados antes do item (sem `item`); um id inventado é 400, não linha órfã.
        pendentes = list(EvolucaoAnexo.objects.filter(id__in=anexos, item__isnull=True))
        if len(pendentes) != len(set(anexos)):
            raise EvolucaoError("Anexo não encontrado.")
        EvolucaoAnexo.objects.filter(id__in=[a.id for a in pendentes]).update(item=item)
    return item


def obter_item(item_id: int) -> EvolucaoItem:
    try:
        return EvolucaoItem.objects.select_related("autor").get(pk=item_id)
    except EvolucaoItem.DoesNotExist as exc:
        raise ItemNaoEncontrado("Item não encontrado.") from exc


def listar_itens(
    user, *, estado: str | None = None, tipo: str | None = None
) -> list[dict[str, Any]]:
    """Quem tria vê tudo; os outros veem o que escreveram. Ordem = ordem de trabalho."""
    qs: QuerySet[EvolucaoItem] = EvolucaoItem.objects.select_related("autor").prefetch_related(
        "anexos"
    )
    if not pode_triar(user):
        qs = qs.filter(autor=user)
    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo=tipo)
    return [serialize_item(item, list(item.anexos.all())) for item in qs]


def pode_ver(user, item: EvolucaoItem) -> bool:
    return pode_triar(user) or (item.autor_id is not None and item.autor_id == user.pk)


@transaction.atomic
def triar(
    item: EvolucaoItem,
    *,
    estado: str | None = None,
    tipo: str | None = None,
    prioridade: Any = NAO_MEXER,
    etiquetas: list[str] | None = None,
    recusa_motivo: str | None = None,
) -> dict[str, Any]:
    """`None` = não mexer, exceto `prioridade` (usa `NAO_MEXER`; `None` = volta a «por triar»).
    Devolve o que mudou, para a auditoria."""
    mudancas: dict[str, Any] = {}
    motivo = (recusa_motivo or "").strip()
    if estado == "recusado" and not motivo:
        raise EvolucaoError("Recusar exige um motivo (recusa_motivo).")
    if motivo and estado != "recusado":
        raise EvolucaoError("recusa_motivo só faz sentido com estado=recusado.")
    if estado is not None and estado != item.estado:
        mudancas["estado"] = [item.estado, estado]
        item.estado = estado
        if estado == "recusado":
            item.recusa_motivo = motivo
            item.recusado_em = timezone.now()
            mudancas["recusa_motivo"] = motivo
    if tipo is not None and tipo != item.tipo:
        mudancas["tipo"] = [item.tipo, tipo]
        item.tipo = tipo
    if prioridade is not NAO_MEXER and prioridade != item.prioridade:
        mudancas["prioridade"] = [item.prioridade, prioridade]
        item.prioridade = prioridade
    if etiquetas is not None:
        novas = sorted({e.strip() for e in etiquetas if e and e.strip()})
        if novas != list(item.etiquetas or []):
            mudancas["etiquetas"] = [list(item.etiquetas or []), novas]
            item.etiquetas = novas
    if mudancas:
        item.save()
    return mudancas


def fechar_por_commit(
    *, codigo: str, commit: str, mensagem: str, deploy_em: datetime
) -> EvolucaoItem | None:
    """Fecha porque o commit que o resolve JÁ ESTÁ em produção (ADR 0006 §3). Devolve `None`,
    sem rebentar, quando não há nada a fazer: código inexistente, já fechado. A primeira
    observação ganha — reescrever `fechado_por` faria o `deploy_em` andar a cada reinício."""
    item = EvolucaoItem.objects.filter(codigo=codigo).first()
    if item is None or item.estado == "feito" or item.fechado_por is not None:
        return None
    item.estado = "feito"
    item.fechado_por = {
        "commit": commit,
        "mensagem": mensagem[:200],
        "deploy_em": deploy_em.isoformat(),
    }
    item.save(update_fields=["estado", "fechado_por", "atualizado_em"])
    return item


def itens_parados(*, agora: datetime, dias: int = DIAS_PARADO_PADRAO) -> list[EvolucaoItem]:
    """Itens abertos sem toque há mais de `dias` que ainda não avisaram (ou voltaram a parar)."""
    limite = agora - timedelta(days=dias)
    return list(
        EvolucaoItem.objects.filter(estado__in=ESTADOS_ABERTOS, atualizado_em__lt=limite)
        .filter(Q(alerta_parado_em__isnull=True) | Q(alerta_parado_em__lt=F("atualizado_em")))
        .order_by("atualizado_em")
    )


def etiquetas_em_uso() -> list[str]:
    """Vocabulário já usado, sem repetições, por ordem alfabética — para sugerir na triagem."""
    todas: set[str] = set()
    for lista in EvolucaoItem.objects.values_list("etiquetas", flat=True):
        todas.update(e for e in (lista or []) if isinstance(e, str))
    return sorted(todas)


def criar_anexo(*, ficheiro, user) -> EvolucaoAnexo:
    """Carrega um ficheiro ANTES do item; o `POST /itens/` liga-o pelos ids."""
    return EvolucaoAnexo.objects.create(
        ficheiro=ficheiro,
        nome_original=getattr(ficheiro, "name", "anexo")[:255],
        content_type=getattr(ficheiro, "content_type", "") or "",
        tamanho=getattr(ficheiro, "size", 0) or 0,
        carregado_por=user if getattr(user, "pk", None) else None,
    )
