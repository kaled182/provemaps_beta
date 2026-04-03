"""
setup_app.services module

Exports runtime_settings for easy access across the application.
"""

from . import runtime_settings, video_gateway

__all__ = ["runtime_settings", "video_gateway"]
