from dataclasses import dataclass, field
import threading

from .config import DEFAULT_GUARD_INTERVAL_SECONDS


@dataclass
class DefenderCache:
    checked_at: float = 0.0
    status: dict | None = None


@dataclass
class AppState:
    ignore_defender: bool = False
    update_guard_enabled: bool = False
    update_guard_interval_seconds: int = DEFAULT_GUARD_INTERVAL_SECONDS
    current_action: str = "Idle"
    activity_log: list[str] = field(default_factory=list)
    shutdown_requested: threading.Event = field(default_factory=threading.Event)
    guard_interval_changed: threading.Event = field(default_factory=threading.Event)
    defender_cache: DefenderCache = field(default_factory=DefenderCache)
    status_lock: threading.Lock = field(default_factory=threading.Lock)
    activity_lock: threading.Lock = field(default_factory=threading.Lock)
    icon: object | None = None
    window: object | None = None
    status_window: object | None = None
    api_instance: object | None = None


STATE = AppState()
