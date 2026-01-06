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
from whatsplay.object.message import Message # Added for mkdocstrings discoverability

__version__ = "1.9.8"

__all__ = ["Client", "BaseWhatsAppClient", "EventHandler", "NoAuth", "LocalProfileAuth", "ChatManager", "StateManager", "Message"] # Added Message

