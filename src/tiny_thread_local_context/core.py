from __future__ import annotations

import threading
from typing import Any, Dict, Iterator


class Context:
    """
    A thread-local carrier for request-scoped values.

    Values set on the main thread are NOT visible inside a worker thread
    automatically: ``threading.local`` isolates each thread by design. To
    propagate values you take an explicit snapshot on the parent thread and
    call :meth:`restore` at the start of the child task.

    Design decisions
    -----------------
    * Snapshot and restore are explicit, not implicit. The caller decides
      when and what to copy, because auto-propagation (e.g. monkeypatching
      ``Thread.run``) has surprising interactions with frameworks that have
      their own thread plumbing.
    * The only mutation surface is :meth:`set`; :meth:`snapshot` returns a
      shallow copy so a restored context is independent of subsequent
      ``set`` calls on either thread.
    * :meth:`restore` REPLACES the local mapping wholesale. Merging would be
      ambiguous (who wins on conflict?) so we keep the contract simple and
      deterministic.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    # -- internal access -------------------------------------------------

    def _state(self) -> Dict[str, Any]:
        state = getattr(self._local, "state", None)
        if state is None:
            state = {}
            self._local.state = state
        return state

    # -- public API ------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Bind ``key`` to ``value`` on the *current* thread only."""
        self._state()[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Return ``key`` from the current thread's view, or ``default``."""
        return self._state().get(key, default)

    def all(self) -> Dict[str, Any]:
        """
        Return a shallow copy of the current thread's bindings.

        A copy (not the live mapping) is returned so callers can iterate or
        stash the result without being affected by later ``set`` calls.
        """
        return dict(self._state())

    def clear(self) -> None:
        """Drop every binding on the current thread."""
        self._local.state = {}

    def snapshot(self) -> Dict[str, Any]:
        """
        Capture the current thread's bindings for transfer to another thread.

        Returns a shallow copy; mutating the returned dict does not affect the
        caller's thread-local state.
        """
        return dict(self._state())

    def restore(self, data: Dict[str, Any]) -> None:
        """
        Replace the current thread's bindings with ``data``.

        Any keys already present on this thread are discarded. The stored
        mapping is copied so later mutations to ``data`` by the caller cannot
        leak into thread-local state.
        """
        self._local.state = dict(data)

    def __contains__(self, key: object) -> bool:
        return key in self._state()

    def __iter__(self) -> Iterator[str]:
        return iter(self._state())

    def __len__(self) -> int:
        return len(self._state())
