"""
Django signals for inventory app.

Phase 7 Day 5 - Cache invalidation hooks.

Automatically invalidates radius search cache when Site locations change,
ensuring cache consistency without manual intervention.
"""
from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from inventory.models import Site

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Site)
def invalidate_radius_cache_on_site_save(
    sender: type[Site],
    instance: Site,
    created: bool,
    **kwargs: Any
) -> None:
    """
    Invalidate radius search cache when Site is created or updated.
    
    Triggered on:
    - New site creation
    - Latitude/longitude changes
    - Site deletion
    
    Args:
        sender: Site model class
        instance: Site instance being saved
        created: True if newly created, False if updated
        **kwargs: Additional signal arguments
    """
    from inventory.cache.radius_search import invalidate_radius_cache
    
    action = "created" if created else "updated"
    
    logger.info(
        "[Signal] Site %s (id=%s) - invalidating radius cache",
        action,
        instance.id
    )
    
    # Invalidate ALL radius search caches
    # (Specific query invalidation would require tracking all active queries)
    deleted_count = invalidate_radius_cache()
    
    logger.debug(
        "[Signal] Invalidated %d cache keys after Site %s",
        deleted_count,
        action
    )


@receiver(post_delete, sender=Site)
def invalidate_radius_cache_on_site_delete(
    sender: type[Site],
    instance: Site,
    **kwargs: Any
) -> None:
    """
    Invalidate radius search cache when Site is deleted.
    
    Args:
        sender: Site model class
        instance: Site instance being deleted
        **kwargs: Additional signal arguments
    """
    from inventory.cache.radius_search import invalidate_radius_cache
    
    logger.info(
        "[Signal] Site deleted (id=%s) - invalidating radius cache",
        instance.id
    )
    
    deleted_count = invalidate_radius_cache()
    
    logger.debug(
        "[Signal] Invalidated %d cache keys after Site deletion",
        deleted_count
    )
