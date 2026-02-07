from typing import List

from rest_framework import serializers

from .models import AlertTemplate


class AlertTemplateSerializer(serializers.ModelSerializer):
    """Serializer para CRUD de modelos de aviso."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    available_placeholders = serializers.SerializerMethodField()

    class Meta:
        model = AlertTemplate
        fields = [
            'id',
            'name',
            'description',
            'category',
            'category_display',
            'channel',
            'channel_display',
            'subject',
            'content',
            'placeholders',
            'is_active',
            'is_default',
            'available_placeholders',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'category_display',
            'channel_display',
            'available_placeholders',
            'created_at',
            'updated_at',
        ]

    def validate_placeholders(self, value: List[str]) -> List[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('placeholders deve ser uma lista de chaves.')
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError('Cada placeholder deve ser uma string.')
            key = item.strip()
            if not key:
                continue
            if key not in cleaned:
                cleaned.append(key)
        return cleaned

    def validate(self, attrs):
        channel = attrs.get('channel', getattr(self.instance, 'channel', None))
        if channel == AlertTemplate.CHANNEL_EMAIL and not attrs.get('subject') and not getattr(self.instance, 'subject', None):
            raise serializers.ValidationError({'subject': 'Defina um assunto para modelos de e-mail.'})
        is_active = attrs.get('is_active', getattr(self.instance, 'is_active', True))
        if attrs.get('is_default') and not is_active:
            raise serializers.ValidationError({'is_default': 'Um modelo inativo não pode ser padrão.'})
        return attrs

    def create(self, validated_data):
        validated_data = self._prepare_placeholders(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._prepare_placeholders(validated_data)
        return super().update(instance, validated_data)

    def _prepare_placeholders(self, validated_data):
        placeholders = validated_data.get('placeholders')
        content = validated_data.get('content')
        if not placeholders:
            placeholders = AlertTemplate.extract_placeholders(content or '')
        validated_data['placeholders'] = placeholders
        return validated_data

    def get_available_placeholders(self, obj: AlertTemplate):
        return obj.available_placeholders()
