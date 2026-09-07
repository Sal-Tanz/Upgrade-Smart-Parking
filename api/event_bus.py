"""Simple async event bus for WebSocket broadcasting."""
import asyncio


class EventBus:
    """Pub/sub event bus using asyncio.Queue for WebSocket broadcasting."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        """Create a new subscriber queue. Returns the queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def publish(self, event: dict):
        """Publish event to all subscribers."""
        for queue in self._subscribers[:]:  # ierate copy to prevent concurent mod
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Skip slow subscribers

    def get(self):
        """Get the singleton instance."""
        return self


# Singleton
event_bus = EventBus()