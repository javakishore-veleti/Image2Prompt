"""Singleton metaclass for the shared-nothing layer components.

Facades / services / DAOs are singletons: one shared, stateless instance per
class. "Shared-nothing" means these instances hold only references to other
singletons (their dependencies) and never per-request mutable state — all
request data flows through ``*Req`` / ``*Resp`` objects, so sharing one instance
across concurrent requests is safe.
"""

from __future__ import annotations

import threading
from abc import ABCMeta


class SingletonMeta(ABCMeta):
    # Derives from ABCMeta so singleton components can also implement ABC
    # interfaces (facades subclass both BaseFacade and an interface ABC).
    _instances: dict[type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def reset(mcs) -> None:
        """Clear all singletons (test isolation only)."""
        with mcs._lock:
            mcs._instances.clear()
