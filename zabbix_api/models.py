"""Deprecated re-export of inventory models.

The canonical definitions now live in ``inventory.models``.  This module keeps
imports backwards compatible while steering callers to the new location.
"""

from __future__ import annotations

from inventory.models import Device, FiberCable, FiberEvent, Port, Site

__all__ = ["Site", "Device", "Port", "FiberCable", "FiberEvent"]
