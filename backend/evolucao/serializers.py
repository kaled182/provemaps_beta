"""Serializers da Central: espelham 1:1 os dicts de `usecases`, sem reordenar chaves."""

from __future__ import annotations

from rest_framework import serializers

from .models import ESTADOS, IMPACTOS, TIPOS


class AnexoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nome_original = serializers.CharField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    tamanho = serializers.IntegerField(read_only=True)


class ItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    codigo = serializers.CharField(read_only=True)
    tipo = serializers.ChoiceField(choices=TIPOS, read_only=True)
    titulo = serializers.CharField(read_only=True)
    descricao = serializers.CharField(read_only=True)
    estado = serializers.ChoiceField(choices=ESTADOS, read_only=True)
    recusa_motivo = serializers.CharField(read_only=True, allow_null=True)
    impacto = serializers.CharField(read_only=True, allow_null=True)
    prioridade = serializers.IntegerField(read_only=True, allow_null=True)
    etiquetas = serializers.ListField(child=serializers.CharField(), read_only=True)
    origem = serializers.CharField(read_only=True)
    autor = serializers.CharField(read_only=True, allow_null=True)
    contexto = serializers.DictField(read_only=True)
    evidencia = serializers.DictField(read_only=True, allow_null=True)
    fechado_por = serializers.DictField(read_only=True, allow_null=True)
    anexos = AnexoSerializer(many=True, read_only=True)
    criado_em = serializers.DateTimeField(read_only=True)
    atualizado_em = serializers.DateTimeField(read_only=True)


class ItemCreateSerializer(serializers.Serializer):
    """Qualquer autenticado reporta. Sem `autor`: vem da sessão, ou a autoria é falsificável."""

    tipo = serializers.ChoiceField(choices=TIPOS)
    titulo = serializers.CharField(min_length=3, max_length=200)
    descricao = serializers.CharField(min_length=3)
    impacto = serializers.ChoiceField(choices=IMPACTOS, required=False, allow_blank=True)
    contexto = serializers.DictField(required=False)
    anexos = serializers.ListField(child=serializers.IntegerField(), required=False)


class ItemTriagemSerializer(serializers.Serializer):
    """Só staff. `prioridade: null` apaga (volta a «por triar»); campo omitido não mexe."""

    estado = serializers.ChoiceField(choices=ESTADOS, required=False)
    tipo = serializers.ChoiceField(choices=TIPOS, required=False)
    prioridade = serializers.IntegerField(min_value=1, max_value=4, required=False, allow_null=True)
    etiquetas = serializers.ListField(child=serializers.CharField(max_length=40), required=False)
    recusa_motivo = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class EtiquetasSerializer(serializers.Serializer):
    etiquetas = serializers.ListField(child=serializers.CharField(), read_only=True)
