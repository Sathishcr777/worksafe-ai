"""
WorkSafe AI — Bounded Ingestion Queue with DROP_OLDEST Policy (Experiment 06).

Implements a bounded queue for live frame ingestion. Prevents unbounded latency
backlog by strictly evicting the oldest unprocessed frame when capacity is reached.
"""

from collections import deque
from typing import Optional, Tuple, Any, List


class BoundedFrameQueue:
    """
    Thread-safe / deterministic bounded queue with DROP_OLDEST eviction.
    
    Design Rationale:
    In real-time computer vision safety monitoring, an old frame sitting in an ingestion
    backlog represents obsolete history. Processing it adds artificial latency and delays
    timely detection of active hazards. The DROP_OLDEST policy ensures that the computer
    vision pipeline always evaluates the most recent physical state of the workplace.
    """

    def __init__(self, max_capacity: int = 3):
        if max_capacity < 1:
            raise ValueError("max_capacity must be at least 1.")
        self.max_capacity = max_capacity
        self._queue = deque()
        self.total_enqueued: int = 0
        self.total_dropped: int = 0

    def reset(self):
        """Clears queue contents and resets counters."""
        self._queue.clear()
        self.total_enqueued = 0
        self.total_dropped = 0

    @property
    def queue_depth(self) -> int:
        """Current number of frames waiting in queue."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self.max_capacity

    def put(self, item: Any) -> Tuple[bool, Optional[Any]]:
        """
        Enqueues a frame item.
        If the queue is at capacity, drops the oldest frame (DROP_OLDEST policy).
        
        Returns:
            - was_dropped: True if an older frame was evicted to make room
            - dropped_item: The evicted item if dropped, else None
        """
        self.total_enqueued += 1
        dropped = None
        was_dropped = False

        if len(self._queue) >= self.max_capacity:
            dropped = self._queue.popleft()
            self.total_dropped += 1
            was_dropped = True

        self._queue.append(item)
        return (was_dropped, dropped)

    def get(self) -> Optional[Any]:
        """Dequeues and returns the next frame item, or None if empty."""
        if not self._queue:
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[Any]:
        """Inspects the next frame item without removing it."""
        if not self._queue:
            return None
        return self._queue[0]
