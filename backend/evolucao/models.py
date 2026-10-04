"""Central de Evolução — o que falta fazer, com autor, data e fila (ADR 0006).

Porte da Central do CRM (ADR 0042 de lá) para Django. Diferenças deliberadas: o ProVeMaps
é um só produto, logo não há `grupo_id`; o autor pode ser nulo (itens abertos pelo agente ou
migrados do quadro); anexos são `FileField` simples (ADR 0006 §4.2).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q

#: Dois, de propósito. A classificação técnica (dívida, dados, segurança) vive em
#: `etiquetas`, que cresce sem migração.
TIPOS = [("problema", "Problema"), ("ideia", "Ideia")]
#: `recusado` é terminal como `feito`, mas pelo motivo oposto — existe para um relato que
#: não vai ser feito ter resposta em vez de apodrecer na Entrada.
ESTADOS = [
    ("entrada", "Entrada"),
    ("aceite", "Aceite"),
    ("a_fazer", "A fazer"),
    ("feito", "Feito"),
    ("recusado", "Recusado"),
]
ESTADOS_ABERTOS = ("entrada", "aceite", "a_fazer")
#: O que QUEM REPORTA diz. A prioridade é de quem tria.
IMPACTOS = [("bloqueia", "Bloqueia"), ("atrasa", "Atrasa"), ("incomoda", "Incomoda")]
ORIGENS = [("humano", "Humano"), ("agente", "Agente")]


class EvolucaoContador(models.Model):
    """O sequencial do `codigo`. Linha única, incrementada atomicamente (`F()` + `UPDATE`):
    um `MAX(codigo)+1` colide sob concorrência e dois itens ficavam com o mesmo número."""

    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Contador da Central"

    @classmethod
    def proximo(cls) -> int:
        # `get_or_create` + `UPDATE ... SET n = n + 1 RETURNING` no mesmo `pk`: o UPDATE é
        # atómico na base; dois pedidos simultâneos recebem números diferentes.
        contador, _ = cls.objects.get_or_create(pk=1)
        cls.objects.filter(pk=contador.pk).update(ultimo_numero=F("ultimo_numero") + 1)
        return cls.objects.values_list("ultimo_numero", flat=True).get(pk=contador.pk)


class EvolucaoItem(models.Model):
    #: `EV-0042`. Referência humana — o id não se diz ao telefone.
    codigo = models.CharField(max_length=12, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default="entrada", db_index=True)
    #: Porque foi recusado. OBRIGATÓRIO ao recusar (CHECK na base).
    recusa_motivo = models.TextField(blank=True, default="")
    recusado_em = models.DateTimeField(null=True, blank=True)
    impacto = models.CharField(max_length=10, choices=IMPACTOS, blank=True, default="")
    #: 1..4. `NULL` = por triar. **Só staff escreve.**
    prioridade = models.PositiveSmallIntegerField(null=True, blank=True)
    etiquetas = models.JSONField(default=list, blank=True)
    #: Da SESSÃO, nunca do corpo do pedido. Nulo em itens do agente ou migrados.
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evolucao_itens",
    )
    #: Rota, viewport, navegador, `request_id` — onde aconteceu.
    contexto = models.JSONField(default=dict, blank=True)
    origem = models.CharField(max_length=10, choices=ORIGENS, default="humano")
    #: Só quando `origem='agente'`: ficheiro, linha, teste que falha, comando (CHECK na base).
    evidencia = models.JSONField(null=True, blank=True)
    #: O que fechou o item: `{commit, mensagem, deploy_em}`. **Escrito por script** (fatia 0027b).
    fechado_por = models.JSONField(null=True, blank=True)
    #: Quando o aviso de «parado há muito» foi dado. Rearma sozinho quando `atualizado_em`
    #: passa à frente.
    alerta_parado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item da Central de Evolução"
        verbose_name_plural = "Itens da Central de Evolução"
        # A ordem da lista É a ordem de trabalho: prioridade (nulos no fim) e depois código.
        ordering = [F("prioridade").asc(nulls_last=True), "codigo"]
        constraints = [
            models.CheckConstraint(
                condition=Q(prioridade__isnull=True) | Q(prioridade__gte=1, prioridade__lte=4),
                name="ck_evolucao_prioridade",
            ),
            models.CheckConstraint(
                condition=~Q(estado="recusado") | ~Q(recusa_motivo=""),
                name="ck_evolucao_recusa_com_motivo",
            ),
            # Um item de agente sem prova é opinião, e opinião não entra na fila.
            models.CheckConstraint(
                condition=~Q(origem="agente") | Q(evidencia__isnull=False),
                name="ck_evolucao_agente_com_prova",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} {self.titulo}"


class EvolucaoAnexo(models.Model):
    """Um print vale mais do que a descrição. Linha própria com FK: um anexo órfão não
    sobrevive ao item."""

    #: Nulo entre o upload e o `POST /itens/` que o reclama; órfãos antigos são lixo a varrer.
    item = models.ForeignKey(
        EvolucaoItem, on_delete=models.CASCADE, related_name="anexos", null=True, blank=True
    )
    ficheiro = models.FileField(upload_to="evolucao/anexos/%Y/%m/")
    nome_original = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True, default="")
    tamanho = models.PositiveIntegerField(default=0)
    carregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.item.codigo if self.item else '—'}: {self.nome_original}"
