"""
Models para gerenciamento de contatos WhatsApp.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


class ContactGroup(models.Model):
    """Grupo de contatos (ex: Clientes, Fornecedores, Equipe)"""
    name = models.CharField(max_length=100, verbose_name="Nome do Grupo")
    description = models.TextField(blank=True, verbose_name="Descrição")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contact_groups',
        verbose_name="Criado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        db_table = 'setup_contact_groups'
        ordering = ['name']
        verbose_name = 'Grupo de Contatos'
        verbose_name_plural = 'Grupos de Contatos'

    def __str__(self):
        return self.name


class Contact(models.Model):
    """Contato para envio de mensagens WhatsApp"""
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Número deve estar no formato: '+5561999999999'. Até 15 dígitos."
    )
    
    name = models.CharField(max_length=200, verbose_name="Nome")
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,
        verbose_name="Telefone"
    )
    email = models.EmailField(blank=True, verbose_name="E-mail")
    company = models.CharField(max_length=200, blank=True, verbose_name="Empresa")
    position = models.CharField(max_length=100, blank=True, verbose_name="Cargo")
    notes = models.TextField(blank=True, verbose_name="Observações")
    
    # Relacionamentos
    groups = models.ManyToManyField(
        ContactGroup,
        blank=True,
        related_name='contacts',
        verbose_name="Grupos"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_contacts',
        verbose_name="Usuário vinculado",
        help_text="Se preenchido, sincroniza com dados do usuário"
    )
    
    # Metadados
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contacts',
        verbose_name="Criado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    # Campos de controle de envio
    last_message_sent = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última mensagem enviada"
    )
    message_count = models.IntegerField(
        default=0,
        verbose_name="Total de mensagens enviadas"
    )
    
    class Meta:
        db_table = 'setup_contacts'
        ordering = ['name']
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    @property
    def formatted_phone(self):
        """Retorna telefone formatado para WhatsApp"""
        # Remove caracteres não numéricos
        phone = ''.join(filter(str.isdigit, self.phone))
        
        # Garante que começa com código do país
        if not phone.startswith('55') and len(phone) == 11:
            phone = '55' + phone
        
        return f"+{phone}" if not phone.startswith('+') else phone


class ImportHistory(models.Model):
    """Histórico de importações de contatos"""
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
    ]
    
    filename = models.CharField(max_length=255, verbose_name="Nome do arquivo")
    file_type = models.CharField(max_length=10, verbose_name="Tipo de arquivo")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    
    total_rows = models.IntegerField(default=0, verbose_name="Total de linhas")
    successful_imports = models.IntegerField(default=0, verbose_name="Importações bem-sucedidas")
    failed_imports = models.IntegerField(default=0, verbose_name="Importações falhas")
    
    error_log = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Log de erros",
        help_text="Lista de erros durante a importação"
    )
    
    imported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contact_imports',
        verbose_name="Importado por"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Concluído em"
    )
    
    class Meta:
        db_table = 'setup_contact_import_history'
        ordering = ['-created_at']
        verbose_name = 'Histórico de Importação'
        verbose_name_plural = 'Histórico de Importações'

    def __str__(self):
        return f"{self.filename} - {self.get_status_display()}"
