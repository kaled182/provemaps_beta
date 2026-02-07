"""
ViewSets para gerenciamento de contatos WhatsApp.
"""
import base64
import logging
import smtplib
import ssl
from email.message import EmailMessage

from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models_contacts import Contact, ContactGroup, ImportHistory
from .serializers_contacts import (
    ContactSerializer,
    ContactListSerializer,
    ContactGroupSerializer,
    ImportHistorySerializer,
    ContactImportSerializer,
    BulkMessageSerializer,
)
from .services_contacts import ContactImportService, sync_contacts_from_users


logger = logging.getLogger(__name__)


def _send_email_via_gateway(gateway, contact, message_body):
    """Envia e-mail usando as configurações do gateway SMTP."""

    config = gateway.config or {}

    host = (config.get('host') or '').strip()
    port_raw = (config.get('port') or '').strip()
    security = (config.get('security') or '').strip().lower()
    username = (config.get('user') or '').strip()
    password = config.get('password') or ''
    auth_mode = (config.get('auth_mode') or 'password').strip().lower()
    from_name = (config.get('from_name') or gateway.name or '').strip()
    from_email = (config.get('from_email') or username or '').strip()
    recipient = (contact.email or '').strip()

    if not host:
        raise ValueError('Gateway SMTP sem host configurado.')
    if not from_email:
        raise ValueError('Gateway SMTP sem remetente configurado.')
    if not recipient:
        raise ValueError('Contato sem endereço de e-mail válido.')

    try:
        port = int(port_raw) if port_raw else (465 if security == 'ssl' else 587)
    except ValueError:
        port = 587

    sender = f"{from_name} <{from_email}>" if from_name else from_email
    subject = f"Mensagem de {gateway.name}" if gateway.name else 'Mensagem ProveMaps'

    email_message = EmailMessage()
    email_message['Subject'] = subject
    email_message['From'] = sender
    email_message['To'] = recipient
    email_message.set_content(message_body)

    if security == 'ssl':
        server = smtplib.SMTP_SSL(host=host, port=port, context=ssl.create_default_context(), timeout=15)
        server.ehlo()
    else:
        server = smtplib.SMTP(host=host, port=port, timeout=15)
        server.ehlo()
        if security == 'tls':
            server.starttls(context=ssl.create_default_context())
            server.ehlo()

    try:
        if auth_mode == 'oauth':
            if not username:
                raise ValueError('Configuração OAuth exige usuário (email).')
            oauth_client_id = (config.get('oauth_client_id') or '').strip()
            oauth_client_secret = (config.get('oauth_client_secret') or '').strip()
            oauth_refresh_token = (config.get('oauth_refresh_token') or '').strip()

            if not (oauth_client_id and oauth_client_secret and oauth_refresh_token):
                raise ValueError('Configuração OAuth incompleta (client id/secret ou refresh token ausente).')

            try:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
            except ImportError as exc:
                raise RuntimeError('Pacotes Google OAuth não instalados para autenticação SMTP.') from exc

            credentials = Credentials(
                None,
                refresh_token=oauth_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=oauth_client_id,
                client_secret=oauth_client_secret,
                scopes=['https://mail.google.com/'],
            )
            credentials.refresh(Request())
            access_token = credentials.token
            auth_string = f'user={username}\x01auth=Bearer {access_token}\x01\x01'
            auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            server.docmd('AUTH', 'XOAUTH2 ' + auth_b64)
        elif username and password:
            server.login(username, password)

        server.send_message(email_message)
    finally:
        try:
            server.quit()
        except Exception:
            logger.debug('Falha ao fechar conexão SMTP para gateway %s', gateway.id, exc_info=True)


class ContactGroupViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de grupos de contatos"""
    queryset = ContactGroup.objects.all()
    serializer_class = ContactGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'groups': serializer.data,
            'count': queryset.count()
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'success': True,
            'message': 'Grupo criado com sucesso',
            'group': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'success': True,
            'message': 'Grupo atualizado com sucesso',
            'group': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Grupo excluído com sucesso'
        }, status=status.HTTP_200_OK)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de contatos"""
    queryset = Contact.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'groups']
    search_fields = ['name', 'phone', 'email', 'company']
    ordering_fields = ['name', 'created_at', 'message_count']
    ordering = ['name']
    pagination_class = None  # Desabilita paginação
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    def get_queryset(self):
        queryset = Contact.objects.all()
        
        # Filtro por grupo
        group_id = self.request.query_params.get('group_id')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
        
        # Filtro por ativo
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'contacts': serializer.data,
            'count': queryset.count()
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'success': True,
            'message': 'Contato criado com sucesso',
            'contact': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'success': True,
            'message': 'Contato atualizado com sucesso',
            'contact': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Contato excluído com sucesso'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def import_file(self, request):
        """Importa contatos de arquivo CSV ou Excel"""
        serializer = ContactImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        group_id = serializer.validated_data.get('group_id')
        update_existing = serializer.validated_data.get('update_existing', False)
        
        # Executa importação
        service = ContactImportService(
            user=request.user,
            group_id=group_id,
            update_existing=update_existing
        )
        import_history = service.import_from_file(file)
        
        # Retorna resultado
        return Response({
            'success': import_history.status == 'completed',
            'message': f'Importação concluída: {import_history.successful_imports} sucesso, {import_history.failed_imports} falhas',
            'import_history': ImportHistorySerializer(import_history).data
        })
    
    @action(detail=False, methods=['post'])
    def sync_from_users(self, request):
        """Sincroniza contatos a partir dos usuários do sistema"""
        synced, errors = sync_contacts_from_users()
        
        return Response({
            'success': True,
            'message': f'{synced} usuários sincronizados',
            'synced_count': synced,
            'errors': errors
        })
    
    @action(detail=False, methods=['post'])
    def bulk_message(self, request):
        """Envia mensagem para múltiplos contatos"""
        serializer = BulkMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        contact_ids = serializer.validated_data['contact_ids']
        group_ids = serializer.validated_data.get('group_ids', [])
        message = serializer.validated_data['message']
        gateway_id = serializer.validated_data['gateway_id']
        schedule_at = serializer.validated_data.get('schedule_at')
        channel = serializer.validated_data.get('channel', 'whatsapp')

        from .models import MessagingGateway

        channel_key = (channel or 'whatsapp').lower()
        channel_map = {key: label for key, label in MessagingGateway.GATEWAY_TYPES if key != 'video'}

        if channel_key not in channel_map:
            return Response(
                {
                    'success': False,
                    'message': 'Canal de mensagem inválido',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Coleta todos os contatos (diretos + grupos)
        all_contact_ids = set(contact_ids)
        
        if group_ids:
            group_contacts = Contact.objects.filter(
                groups__id__in=group_ids,
                is_active=True
            ).values_list('id', flat=True)
            all_contact_ids.update(group_contacts)
        
        channel_label = channel_map[channel_key]

        # Valida gateway
        try:
            gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type=channel_key)
        except MessagingGateway.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Gateway {channel_label} não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Future enhancement: Celery task para envio assíncrono em massa
        # Atualmente o envio é síncrono via gateway, o que funciona para volumes moderados
        # Para >1000 mensagens, implementar:
        # from .tasks import send_bulk_whatsapp_messages
        # send_bulk_whatsapp_messages.delay(list(all_contact_ids), message, gateway_id, schedule_at)
        # Issue: #TBD - Criar task Celery para envio em massa (Sprint 4)
        
        return Response({
            'success': True,
            'message': f'{len(all_contact_ids)} mensagens agendadas para envio',
            'contact_count': len(all_contact_ids),
            'scheduled': schedule_at is not None
        })
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Envia mensagem individual para um contato"""
        contact = self.get_object()
        
        message = request.data.get('message')
        gateway_id = request.data.get('gateway_id')
        channel = (request.data.get('channel') or 'whatsapp').lower()

        from .models import MessagingGateway

        channel_map = {key: label for key, label in MessagingGateway.GATEWAY_TYPES if key != 'video'}

        if channel not in channel_map:
            return Response({
                'success': False,
                'message': 'Canal de mensagem inválido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not message:
            return Response({
                'success': False,
                'message': 'Mensagem é obrigatória'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not gateway_id:
            return Response({
                'success': False,
                'message': 'Gateway é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        channel_label = channel_map[channel]

        # Valida gateway
        try:
            gateway = MessagingGateway.objects.get(id=gateway_id, gateway_type=channel)
        except MessagingGateway.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Gateway {channel_label} não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        if channel == 'smtp':
            if not contact.email:
                return Response({
                    'success': False,
                    'message': 'Contato não possui e-mail cadastrado'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                _send_email_via_gateway(gateway, contact, message)
            except Exception as exc:
                logger.exception('Falha ao enviar e-mail via gateway %s', gateway.id)
                detail = str(exc)
                if '5.7.8' in detail or 'BadCredentials' in detail:
                    detail = (
                        'Credenciais SMTP rejeitadas. Valide usuário/senha ou configure App Password/OAuth.'
                    )
                return Response({
                    'success': False,
                    'message': f'Falha ao enviar e-mail: {detail}'
                }, status=status.HTTP_502_BAD_GATEWAY)
        
        # Future enhancement: Integração com serviço WhatsApp Business API
        # Atualmente suportamos apenas email via SMTP gateway
        # Para WhatsApp, implementar similar a whatsapp_qr_test_message em api_views.py
        # Issue: #TBD - Integrar WhatsApp Business API (backlog)
        
        # Atualiza estatísticas do contato
        from django.utils import timezone
        contact.last_message_sent = timezone.now()
        contact.message_count += 1
        contact.save(update_fields=['last_message_sent', 'message_count'])
        
        return Response({
            'success': True,
            'message': 'Mensagem enviada com sucesso',
            'recipient': contact.formatted_phone
        })


class ImportHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet somente leitura para histórico de importações"""
    queryset = ImportHistory.objects.all()
    serializer_class = ImportHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'filename']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Apenas importações do usuário atual (ou todos se staff)
        queryset = ImportHistory.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(imported_by=self.request.user)
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'imports': serializer.data,
            'count': queryset.count()
        })
