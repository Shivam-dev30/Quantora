"""Asynchronous Event Bus implementing decoupled pub/sub for market events."""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Type, TypeVar
from backend.app.core.logging import get_logger

logger = get_logger("event_bus")

T = TypeVar("T")
EventHandler = Callable[[T], Coroutine[Any, Any, None]]


class EventBus:
    """Decoupled asynchronous event distributor for market and alert events."""

    def __init__(self, queue_maxsize: int = 10000) -> None:
        self._subscribers: Dict[Type[Any], List[EventHandler]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_maxsize)
        self._running: bool = False
        self._worker_task: asyncio.Task | None = None

    def subscribe(self, event_type: Type[T], handler: EventHandler[T]) -> None:
        """Register an async handler function for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to event {event_type.__name__}")

    def unsubscribe(self, event_type: Type[T], handler: EventHandler[T]) -> None:
        """Unregister an async handler."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: Any) -> None:
        """Enqueue an event for asynchronous processing without blocking the caller."""
        if not self._running:
            # If worker is not running, dispatch immediately to avoid dropping events
            await self._dispatch_event(event)
            return

        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.error(
                f"EventBus queue is full! Dropping event of type {type(event).__name__}"
            )

    async def _dispatch_event(self, event: Any) -> None:
        """Dispatch event concurrently to all registered subscribers."""
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        # Also support polymorphic dispatch if handlers subscribed to superclass
        for sub_type, sub_handlers in self._subscribers.items():
            if sub_type != event_type and isinstance(event, sub_type):
                handlers.extend([h for h in sub_handlers if h not in handlers])

        if not handlers:
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._safe_invoke(handler, event))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, handler: EventHandler, event: Any) -> None:
        """Invoke an event handler capturing exceptions so one handler cannot break others."""
        try:
            await handler(event)
        except Exception as e:
            logger.exception(
                f"Error in event handler {handler.__name__} for {type(event).__name__}: {e}"
            )

    async def _worker_loop(self) -> None:
        """Background worker consuming events from the queue."""
        while self._running:
            try:
                event = await self._queue.get()
                await self._dispatch_event(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Unexpected error in EventBus worker: {e}")

    async def start(self) -> None:
        """Start the background event consumer worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("EventBus background worker started.")

    async def stop(self) -> None:
        """Stop worker and drain remaining queued events."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("EventBus stopped.")


# Global EventBus singleton instance
_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
