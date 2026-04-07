from __future__ import annotations

import asyncio
from collections import defaultdict
from threading import Lock
from uuid import uuid4


class EventBroker:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = Lock()
        self._subscribers: dict[str, dict[str, asyncio.Queue]] = defaultdict(dict)

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def subscribe(self, topic: str) -> tuple[str, asyncio.Queue]:
        subscriber_id = uuid4().hex
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers[topic][subscriber_id] = queue
        return subscriber_id, queue

    async def unsubscribe(self, topic: str, subscriber_id: str) -> None:
        with self._lock:
            subscribers = self._subscribers.get(topic)
            if subscribers is None:
                return
            subscribers.pop(subscriber_id, None)
            if not subscribers:
                self._subscribers.pop(topic, None)

    def publish(self, topic: str, payload: dict) -> None:
        if self._loop is None:
            return
        with self._lock:
            queues = list(self._subscribers.get(topic, {}).values())
        for queue in queues:
            self._loop.call_soon_threadsafe(queue.put_nowait, payload)
