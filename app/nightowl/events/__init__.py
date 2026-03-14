"""Event bus and runtime event exports."""

from .broadcaster import RuntimeBroadcaster
from .schemas import RuntimeEvent
from .translate import translate_runtime_event

__all__ = ["EventBus", "RuntimeBroadcaster", "RuntimeEvent", "translate_runtime_event"]


def __getattr__(name: str):
    if name == "EventBus":
        from .bus import EventBus

        return EventBus
    raise AttributeError(name)
