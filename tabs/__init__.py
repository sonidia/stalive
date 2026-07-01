from .host import HostTab
from .modal import PingModal
from .proxy import ProxyTab

PingTab = ProxyTab
CheckPortTab = HostTab

__all__ = [
    "CheckPortTab",
    "HostTab",
    "PingModal",
    "PingTab",
    "ProxyTab",
]
