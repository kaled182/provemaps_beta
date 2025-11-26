"""
Service layer for ImportRule application logic.
Applies regex-based auto-categorization during device import from Zabbix.
"""
import re
from typing import Dict, Optional

from inventory.models import ImportRule


def apply_import_rules(device_name: str) -> Optional[Dict[str, any]]:
    """
    Apply active import rules to a device name.
    
    Returns first matching rule's category and group, or None if no match.
    Rules are evaluated in priority order (lowest number first).
    
    Args:
        device_name: Name of device being imported (e.g., "OLT-01-CENTRO")
    
    Returns:
        {
            "category": "gpon",
            "group_id": 123,
            "rule_id": 45,
            "rule_description": "OLTs Huawei"
        }
        or None if no rules match
    
    Example:
        result = apply_import_rules("OLT-HUAWEI-001")
        if result:
            device.category = result["category"]
            if result["group_id"]:
                device.monitoring_group_id = result["group_id"]
    """
    rules = (
        ImportRule.objects
        .filter(is_active=True)
        .select_related('group')
        .order_by('priority', 'id')
    )
    
    for rule in rules:
        try:
            # Case-insensitive regex match
            if re.match(rule.pattern, device_name, re.IGNORECASE):
                return {
                    "category": rule.category,
                    "group_id": rule.group_id,
                    "rule_id": rule.id,
                    "rule_description": rule.description or rule.pattern,
                }
        except re.error:
            # Skip invalid patterns (shouldn't happen due to serializer validation)
            continue
    
    return None
