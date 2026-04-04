"""Tests for setup_app.serializers_contacts — ContactGroup, Contact, ImportHistory."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase


class ContactGroupSerializerTests(TestCase):
    def _make_group(self, **kwargs):
        group = MagicMock()
        group.id = kwargs.get("id", 1)
        group.name = kwargs.get("name", "Test Group")
        group.description = kwargs.get("description", "")
        group.created_by = kwargs.get("created_by", None)
        group.created_at = kwargs.get("created_at", None)
        group.updated_at = kwargs.get("updated_at", None)
        # contacts.filter(...).count()
        group.contacts.filter.return_value.count.return_value = kwargs.get(
            "contact_count", 3
        )
        return group

    def test_get_contact_count(self):
        from setup_app.serializers_contacts import ContactGroupSerializer
        group = self._make_group(contact_count=5)
        s = ContactGroupSerializer()
        count = s.get_contact_count(group)
        self.assertEqual(count, 5)

    def test_get_created_by_name_with_user(self):
        from setup_app.serializers_contacts import ContactGroupSerializer
        group = self._make_group()
        group.created_by = MagicMock()
        group.created_by.get_full_name.return_value = "João Silva"
        s = ContactGroupSerializer()
        name = s.get_created_by_name(group)
        self.assertEqual(name, "João Silva")

    def test_get_created_by_name_without_user(self):
        from setup_app.serializers_contacts import ContactGroupSerializer
        group = self._make_group()
        group.created_by = None
        s = ContactGroupSerializer()
        name = s.get_created_by_name(group)
        self.assertIsNone(name)


class ContactSerializerTests(TestCase):
    def _make_contact(self, **kwargs):
        contact = MagicMock()
        contact.id = kwargs.get("id", 1)
        contact.name = kwargs.get("name", "Alice")
        contact.phone = kwargs.get("phone", "+5511987654321")
        contact.created_by = kwargs.get("created_by", None)
        contact.user = kwargs.get("user", None)
        groups = kwargs.get("groups", [MagicMock(name="Sales")])
        contact.groups.all.return_value = groups
        return contact

    def test_get_group_names(self):
        from setup_app.serializers_contacts import ContactSerializer
        contact = self._make_contact()
        grp = MagicMock()
        grp.name = "Sales"
        contact.groups.all.return_value = [grp]
        s = ContactSerializer()
        names = s.get_group_names(contact)
        self.assertEqual(names, ["Sales"])

    def test_get_created_by_name_with_user(self):
        from setup_app.serializers_contacts import ContactSerializer
        contact = self._make_contact()
        contact.created_by = MagicMock()
        contact.created_by.get_full_name.return_value = "Admin User"
        s = ContactSerializer()
        self.assertEqual(s.get_created_by_name(contact), "Admin User")

    def test_get_created_by_name_without_user(self):
        from setup_app.serializers_contacts import ContactSerializer
        contact = self._make_contact()
        contact.created_by = None
        s = ContactSerializer()
        self.assertIsNone(s.get_created_by_name(contact))

    def test_get_user_name_with_user(self):
        from setup_app.serializers_contacts import ContactSerializer
        contact = self._make_contact()
        contact.user = MagicMock()
        contact.user.get_full_name.return_value = "User Name"
        contact.user.username = "username"
        s = ContactSerializer()
        result = s.get_user_name(contact)
        self.assertIsNotNone(result)

    def test_get_user_name_without_user(self):
        from setup_app.serializers_contacts import ContactSerializer
        contact = self._make_contact()
        contact.user = None
        s = ContactSerializer()
        self.assertIsNone(s.get_user_name(contact))


class ImportHistorySerializerTests(TestCase):
    def _make_history(self, **kwargs):
        h = MagicMock()
        h.id = kwargs.get("id", 1)
        h.filename = kwargs.get("filename", "contacts.csv")
        h.status = kwargs.get("status", "completed")
        h.imported_by = kwargs.get("imported_by", None)
        h.total_rows = kwargs.get("total_rows", 10)
        h.successful_imports = kwargs.get("successful_imports", 9)
        h.failed_imports = kwargs.get("failed_imports", 1)
        return h

    def test_get_imported_by_name_with_user(self):
        from setup_app.serializers_contacts import ImportHistorySerializer
        h = self._make_history()
        h.imported_by = MagicMock()
        h.imported_by.get_full_name.return_value = "Manager"
        s = ImportHistorySerializer()
        name = s.get_imported_by_name(h)
        self.assertEqual(name, "Manager")

    def test_get_imported_by_name_without_user(self):
        from setup_app.serializers_contacts import ImportHistorySerializer
        h = self._make_history()
        h.imported_by = None
        s = ImportHistorySerializer()
        self.assertIsNone(s.get_imported_by_name(h))
