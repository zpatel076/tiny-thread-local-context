# tiny-thread-local-context

A small carrier object that stores request-scoped values per thread using `threading.local`, with explicit `snapshot()` and `restore()` for handing values to worker threads.

```python
from tiny_thread_local_context import Context

ctx = Context()
ctx.set("request_id", "req-123")

snap = ctx.snapshot()  # capture on the parent thread

def worker():
    ctx.restore(snap) # rehydrate inside the worker thread
    print(ctx.get("request_id"))

import threading
threading.Thread(target=worker).start()
```

## Why this exists

`threading.local` deliberately isolates each thread, so request-scoped values set on the main thread do not reach a worker thread by default. This library makes the transfer explicit: you `snapshot()` on the parent and `restore()` at the start of the child task. No monkeypatching of `Thread.run`, no global registry — the caller controls when and what to copy, which matters when a framework already has its own thread plumbing.

`restore()` replaces the current thread's bindings wholesale rather than merging. Merging forces a conflict policy (who wins on duplicate keys?) and the library would rather expose one deterministic rule than an option surface that gets the wrong default for half its users.

## The awkward edge

`snapshot()` and `restore()` perform shallow copies. That is fine for strings, ints, and other immutable identifiers, but mutable values (lists, dicts) are shared by reference between threads. If you stash a mutable object in the context and mutate it from a worker, the parent sees the mutation. Put immutables in the context, or copy mutables yourself before storing them.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

