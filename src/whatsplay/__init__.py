"""
Main module exports for whatsplay library
"""

from whatsplay.client import Client
from whatsplay.base_client import BaseWhatsAppClient
from whatsplay.events.event_handler import EventHandler
from whatsplay.auth.local_profile_auth import LocalProfileAuth
from whatsplay.auth.no_auth import NoAuth
from whatsplay.chat_manager import ChatManager
from whatsplay.state_manager import StateManager
from whatsplay.object.message import (
    BUBBLE_WALK_DEPTH,
    CONTAINER_WALK_DEPTH,
    DIRECTION_ORDER,
    POSITIONAL_ABSTAIN_RATIO,
    POSITIONAL_SIDE_JS,
    DirectionSignal,
    Message,
    FileMessage,
    VoiceMessage,
    get_direction_fallback_count,
    normalize_sender_name,
    normalize_own_push_names,
    reset_direction_fallback_count,
)
from whatsplay.codec_detector import detect_codec, get_codec_name

__version__ = "2.5.1"

__all__ = [
    "Client",
    "BaseWhatsAppClient",
    "EventHandler",
    "NoAuth",
    "LocalProfileAuth",
    "ChatManager",
    "StateManager",
    "Message",
    "FileMessage",
    "VoiceMessage",
    "DirectionSignal",
    "DIRECTION_ORDER",
    "POSITIONAL_SIDE_JS",
    "POSITIONAL_ABSTAIN_RATIO",
    "BUBBLE_WALK_DEPTH",
    "CONTAINER_WALK_DEPTH",
    "get_direction_fallback_count",
    "reset_direction_fallback_count",
    "normalize_sender_name",
    "normalize_own_push_names",
    "detect_codec",
    "get_codec_name",
]

