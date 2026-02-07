"""ViewSets relacionados a modelos de aviso."""

from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AlertTemplate
from .serializers_alert_templates import AlertTemplateSerializer


class AlertTemplateViewSet(viewsets.ModelViewSet):
    queryset = AlertTemplate.objects.all()
    serializer_class = AlertTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'content']
    ordering_fields = ['name', 'updated_at', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        channel = self.request.query_params.get('channel')
        if channel:
            queryset = queryset.filter(channel=channel)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        meta = {
            'categories': AlertTemplate.CATEGORY_CHOICES,
            'channels': AlertTemplate.CHANNEL_CHOICES,
            'placeholders': AlertTemplate.placeholder_catalog(),
            'count': len(serializer.data),
            'defaults': [
                {
                    'category': template.category,
                    'channel': template.channel,
                    'id': template.id,
                }
                for template in AlertTemplate.objects.filter(is_default=True, is_active=True)
            ],
        }

        return Response({
            'success': True,
            'templates': serializer.data,
            'meta': meta,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user, updated_by=request.user)
        response_data = self.get_serializer(instance).data
        return Response({
            'success': True,
            'message': 'Modelo criado com sucesso',
            'template': response_data,
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(updated_by=request.user)
        response_data = self.get_serializer(instance).data
        return Response({
            'success': True,
            'message': 'Modelo atualizado com sucesso',
            'template': response_data,
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Modelo excluído com sucesso',
        }, status=status.HTTP_200_OK)
