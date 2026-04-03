"""
Serviço para importação de contatos de arquivos CSV/Excel.
"""
import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Tuple

import openpyxl
from django.db import transaction, models
from django.contrib.auth import get_user_model

from .models_contacts import Contact, ContactGroup, ImportHistory

User = get_user_model()
logger = logging.getLogger(__name__)


class ContactImportService:
    """Serviço para importação de contatos"""
    
    REQUIRED_FIELDS = ['name', 'phone']
    OPTIONAL_FIELDS = ['email', 'company', 'position', 'notes']
    
    def __init__(self, user, group_id=None, update_existing=False):
        self.user = user
        self.group_id = group_id
        self.update_existing = update_existing
        self.errors = []
    
    def import_from_file(self, file) -> ImportHistory:
        """
        Importa contatos de arquivo CSV ou Excel.
        
        Args:
            file: Arquivo uploaded (InMemoryUploadedFile ou TemporaryUploadedFile)
        
        Returns:
            ImportHistory: Registro do histórico de importação
        """
        import_history = ImportHistory.objects.create(
            filename=file.name,
            file_type=self._get_file_extension(file.name),
            status='processing',
            imported_by=self.user,
        )
        
        try:
            # Lê dados do arquivo
            if file.name.endswith('.csv'):
                rows = self._read_csv(file)
            else:
                rows = self._read_excel(file)
            
            import_history.total_rows = len(rows)
            import_history.save()
            
            # Processa linhas
            successful, failed = self._process_rows(rows, import_history)
            
            # Atualiza histórico
            import_history.successful_imports = successful
            import_history.failed_imports = failed
            import_history.status = 'completed'
            import_history.completed_at = datetime.now()
            import_history.error_log = self.errors
            import_history.save()
            
            logger.info(
                f"Importação concluída: {successful} sucesso, {failed} falhas"
            )
            
        except Exception as e:
            logger.error(f"Erro na importação: {e}", exc_info=True)
            import_history.status = 'failed'
            import_history.error_log = [{'error': str(e)}]
            import_history.save()
        
        return import_history
    
    def _read_csv(self, file) -> List[Dict]:
        """Lê arquivo CSV e retorna lista de dicts"""
        rows = []
        content = file.read()
        
        # Tenta diferentes encodings
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
            try:
                decoded = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Não foi possível decodificar o arquivo CSV")
        
        reader = csv.DictReader(io.StringIO(decoded))
        
        for row in reader:
            # Normaliza keys (lowercase, remove espaços)
            normalized_row = {
                self._normalize_key(k): v.strip() if v else ''
                for k, v in row.items()
            }
            rows.append(normalized_row)
        
        return rows
    
    def _read_excel(self, file) -> List[Dict]:
        """Lê arquivo Excel e retorna lista de dicts"""
        rows = []
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        
        # Primeira linha como headers
        headers = [self._normalize_key(cell.value) for cell in sheet[1]]
        
        # Lê dados
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_dict = {}
            for header, value in zip(headers, row):
                row_dict[header] = str(value).strip() if value else ''
            rows.append(row_dict)
        
        return rows
    
    def _process_rows(self, rows: List[Dict], import_history: ImportHistory) -> Tuple[int, int]:
        """
        Processa linhas importadas.
        
        Returns:
            Tuple[int, int]: (sucessos, falhas)
        """
        successful = 0
        failed = 0
        
        group = None
        if self.group_id:
            try:
                group = ContactGroup.objects.get(id=self.group_id)
            except ContactGroup.DoesNotExist:
                logger.warning(f"Grupo {self.group_id} não encontrado")
        
        for idx, row in enumerate(rows, start=2):  # start=2 porque linha 1 é header
            try:
                contact = self._create_or_update_contact(row, group)
                if contact:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                error_msg = {
                    'row': idx,
                    'data': row,
                    'error': str(e)
                }
                self.errors.append(error_msg)
                logger.error(f"Erro na linha {idx}: {e}")
        
        return successful, failed
    
    @transaction.atomic
    def _create_or_update_contact(self, row: Dict, group: ContactGroup = None) -> Contact:
        """
        Cria ou atualiza contato.
        
        Returns:
            Contact: Contato criado/atualizado ou None se falhou
        """
        # Valida campos obrigatórios
        name = row.get('name') or row.get('nome')
        phone = row.get('phone') or row.get('telefone') or row.get('celular')
        
        if not name or not phone:
            raise ValueError(f"Campos obrigatórios faltando: name={name}, phone={phone}")
        
        # Normaliza telefone
        phone = self._normalize_phone(phone)
        
        # Verifica se já existe
        existing = Contact.objects.filter(phone=phone).first()
        
        if existing and not self.update_existing:
            raise ValueError(f"Contato já existe: {phone}")
        
        # Prepara dados
        contact_data = {
            'name': name,
            'phone': phone,
            'email': row.get('email') or row.get('e-mail') or '',
            'company': row.get('company') or row.get('empresa') or '',
            'position': row.get('position') or row.get('cargo') or '',
            'notes': row.get('notes') or row.get('observacoes') or row.get('obs') or '',
        }
        
        # Cria ou atualiza
        if existing:
            for key, value in contact_data.items():
                setattr(existing, key, value)
            contact = existing
        else:
            contact = Contact(**contact_data)
            contact.created_by = self.user
        
        contact.save()
        
        # Adiciona ao grupo se especificado
        if group:
            contact.groups.add(group)
        
        return contact
    
    @staticmethod
    def _normalize_key(key: str) -> str:
        """Normaliza chave do CSV/Excel"""
        if not key:
            return ''
        return key.lower().strip().replace(' ', '_')
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normaliza número de telefone"""
        # Remove tudo exceto dígitos
        phone = ''.join(filter(str.isdigit, phone))
        
        # Se tem 11 dígitos (celular BR sem DDI)
        if len(phone) == 11:
            phone = '55' + phone
        # Se tem 10 dígitos (fixo BR sem DDI)
        elif len(phone) == 10:
            phone = '55' + phone
        
        # Adiciona +
        return f"+{phone}"
    
    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Retorna extensão do arquivo"""
        import os
        return os.path.splitext(filename)[1].lower()


def sync_contacts_from_users():
    """
    Sincroniza contatos a partir dos usuários do sistema.
    Cria/atualiza contatos para usuários que têm telefone.
    """
    from django.contrib.auth import get_user_model
    from core.models import UserProfile
    
    User = get_user_model()
    
    # Busca usuários ativos que possuem telefone no perfil
    users_with_phone = User.objects.filter(
        is_active=True,
        profile__phone_number__isnull=False
    ).exclude(
        profile__phone_number=''
    ).select_related('profile')
    
    synced = 0
    errors = []
    
    for user in users_with_phone:
        try:
            # Pega telefone do perfil
            profile = user.profile
            if not profile or not profile.phone_number:
                continue
            
            # Tenta encontrar contato existente vinculado ao usuário
            contact = Contact.objects.filter(user=user).first()
            
            if not contact:
                # Tenta encontrar por telefone
                phone = ContactImportService._normalize_phone(profile.phone_number)
                contact = Contact.objects.filter(phone=phone).first()
            
            if contact:
                # Atualiza dados
                contact.name = user.get_full_name() or user.username
                contact.email = user.email
                contact.user = user
                contact.save()
            else:
                # Cria novo contato
                Contact.objects.create(
                    name=user.get_full_name() or user.username,
                    phone=ContactImportService._normalize_phone(profile.phone_number),
                    email=user.email,
                    user=user,
                    is_active=True,
                )
            
            synced += 1
            
        except Exception as e:
            errors.append({
                'user_id': user.id,
                'username': user.username,
                'error': str(e)
            })
            logger.error(f"Erro ao sincronizar usuário {user.id}: {e}")
    
    logger.info(f"Sincronização concluída: {synced} usuários sincronizados")
    
    return synced, errors

