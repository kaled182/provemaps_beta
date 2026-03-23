"""
Serializers para gerenciamento de contatos WhatsApp.
"""
from rest_framework import serializers
from .models_contacts import Contact, ContactGroup, ImportHistory


class ContactGroupSerializer(serializers.ModelSerializer):
    """Serializer para grupos de contatos"""
    contact_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactGroup
        fields = [
            'id',
            'name',
            'description',
            'contact_count',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_contact_count(self, obj):
        return obj.contacts.filter(is_active=True).count()
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class ContactSerializer(serializers.ModelSerializer):
    """Serializer para contatos"""
    group_names = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    formatted_phone = serializers.ReadOnlyField()
    
    class Meta:
        model = Contact
        fields = [
            'id',
            'name',
            'phone',
            'formatted_phone',
            'email',
            'company',
            'position',
            'notes',
            'groups',
            'group_names',
            'user',
            'user_name',
            'is_active',
            'last_message_sent',
            'message_count',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_by',
            'created_at',
            'updated_at',
            'last_message_sent',
            'message_count',
            'formatted_phone',
        ]
    
    def get_group_names(self, obj):
        return [group.name for group in obj.groups.all()]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None
    
    def validate_phone(self, value):
        """Valida e normaliza o número de telefone"""
        # Remove caracteres não numéricos
        phone = ''.join(filter(str.isdigit, value))
        
        # Deve ter entre 10 e 15 dígitos
        if len(phone) < 10 or len(phone) > 15:
            raise serializers.ValidationError(
                "Número deve ter entre 10 e 15 dígitos."
            )
        
        # Adiciona + no início se não tiver
        if not value.startswith('+'):
            value = f"+{phone}"
        
        return value


class ContactListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listagem de contatos"""
    group_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id',
            'name',
            'phone',
            'email',
            'company',
            'group_names',
            'is_active',
            'message_count',
        ]
    
    def get_group_names(self, obj):
        return [group.name for group in obj.groups.all()]


class ImportHistorySerializer(serializers.ModelSerializer):
    """Serializer para histórico de importações"""
    imported_by_name = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ImportHistory
        fields = [
            'id',
            'filename',
            'file_type',
            'status',
            'total_rows',
            'successful_imports',
            'failed_imports',
            'success_rate',
            'error_log',
            'imported_by',
            'imported_by_name',
            'created_at',
            'completed_at',
            'duration',
        ]
        read_only_fields = [
            'imported_by',
            'created_at',
            'completed_at',
        ]
    
    def get_imported_by_name(self, obj):
        return obj.imported_by.get_full_name() if obj.imported_by else None
    
    def get_duration(self, obj):
        """Retorna duração da importação em segundos"""
        if obj.completed_at and obj.created_at:
            delta = obj.completed_at - obj.created_at
            return delta.total_seconds()
        return None
    
    def get_success_rate(self, obj):
        """Retorna taxa de sucesso em percentual"""
        if obj.total_rows > 0:
            return round((obj.successful_imports / obj.total_rows) * 100, 2)
        return 0.0


class ContactImportSerializer(serializers.Serializer):
    """Serializer para upload de arquivo de importação"""
    file = serializers.FileField()
    group_id = serializers.IntegerField(required=False, allow_null=True)
    update_existing = serializers.BooleanField(default=False)
    
    def validate_file(self, value):
        """Valida o arquivo de importação"""
        valid_extensions = ['.csv', '.xls', '.xlsx']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"Formato de arquivo não suportado. Use: {', '.join(valid_extensions)}"
            )
        
        # Limita tamanho do arquivo a 5MB
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Arquivo muito grande. Tamanho máximo: 5MB"
            )
        
        return value


class BulkMessageSerializer(serializers.Serializer):
    """Serializer para envio de mensagens em massa"""
    contact_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="IDs dos contatos que receberão a mensagem"
    )
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="IDs dos grupos cujos contatos receberão a mensagem"
    )
    message = serializers.CharField(
        max_length=4096,
        help_text="Mensagem a ser enviada"
    )
    gateway_id = serializers.IntegerField(
        help_text="ID do gateway utilizado para envio"
    )
    schedule_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Data/hora para agendamento (opcional)"
    )
    channel = serializers.ChoiceField(
        choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('telegram', 'Telegram'), ('smtp', 'SMTP')],
        required=False,
        help_text="Canal de envio da mensagem"
    )
    
    def validate_message(self, value):
        """Valida a mensagem"""
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Mensagem não pode estar vazia.")
        return value
