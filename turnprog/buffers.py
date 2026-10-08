"""
Message buffer implementation following Carlson (1986).
Includes three-state incoming framing (Ready, Partial, Complete)
and client-side/server-side outbound message buffering.
"""

from __future__ import annotations
import collections
import json
import logging
from typing import Deque, List, Optional, Tuple
from .models import BufferState, Message

logger = logging.getLogger("turnprog.buffers")


class MessageFramingBuffer:
    """
    Implements the 3-state input framing buffer specified by Carlson (1986):
    - READY_FOR_MESSAGE: Idle, awaiting start of new message frame
    - PARTIAL_MESSAGE: Initial fragment received, waiting for complete transmission
    - COMPLETE_MESSAGE: Complete message parsed and queued for the Game Master
    """

    DELIMITER = b"\n"

    def __init__(self, player_id: str, max_queue_size: int = 100):
        self.player_id = player_id
        self.max_queue_size = max_queue_size
        self._raw_stream_buffer = bytearray()
        self._state: BufferState = BufferState.READY_FOR_MESSAGE
        self._completed_messages: Deque[Message] = collections.deque()
        self._outbound_queue: Deque[Message] = collections.deque()
        self._dropped_message_count: int = 0

    @property
    def state(self) -> BufferState:
        return self._state

    @property
    def pending_count(self) -> int:
        return len(self._completed_messages)

    @property
    def outbound_count(self) -> int:
        return len(self._outbound_queue)

    def feed_bytes(self, chunk: bytes) -> List[Message]:
        """
        Feeds incoming network bytes into the buffer.
        Transitions between READY_FOR_MESSAGE, PARTIAL_MESSAGE, and COMPLETE_MESSAGE.
        Returns any newly completed messages.
        """
        if not chunk:
            return []

        self._raw_stream_buffer.extend(chunk)
        newly_completed: List[Message] = []

        # Check state transition: if we have raw bytes, we are at least PARTIAL
        if len(self._raw_stream_buffer) > 0:
            self._state = BufferState.PARTIAL_MESSAGE

        while self.DELIMITER in self._raw_stream_buffer:
            delim_idx = self._raw_stream_buffer.index(self.DELIMITER)
            line_bytes = bytes(self._raw_stream_buffer[:delim_idx]).strip()
            # Advance stream buffer past the delimiter
            del self._raw_stream_buffer[: delim_idx + len(self.DELIMITER)]

            if not line_bytes:
                continue

            try:
                line_str = line_bytes.decode("utf-8")
                msg_dict = json.loads(line_str)
                msg = Message.from_dict(msg_dict)
                self._enqueue_completed(msg)
                newly_completed.append(msg)
            except Exception as e:
                logger.warning(f"Failed to parse message from {self.player_id}: {e}")

        # Update buffer state based on remaining raw stream buffer and queue
        if len(self._completed_messages) > 0:
            self._state = BufferState.COMPLETE_MESSAGE
        elif len(self._raw_stream_buffer) > 0:
            self._state = BufferState.PARTIAL_MESSAGE
        else:
            self._state = BufferState.READY_FOR_MESSAGE

        return newly_completed

    def _enqueue_completed(self, msg: Message) -> None:
        if len(self._completed_messages) >= self.max_queue_size:
            # Drop oldest message to prevent unbounded memory growth
            self._completed_messages.popleft()
            self._dropped_message_count += 1
            logger.warning(f"Queue overflow for player {self.player_id}, dropped oldest message")
        self._completed_messages.append(msg)
        self._state = BufferState.COMPLETE_MESSAGE

    def pop_message(self) -> Optional[Message]:
        """Consumes the next complete message for processing by the Game Master."""
        if not self._completed_messages:
            if len(self._raw_stream_buffer) > 0:
                self._state = BufferState.PARTIAL_MESSAGE
            else:
                self._state = BufferState.READY_FOR_MESSAGE
            return None

        msg = self._completed_messages.popleft()

        # Update state after popping
        if len(self._completed_messages) > 0:
            self._state = BufferState.COMPLETE_MESSAGE
        elif len(self._raw_stream_buffer) > 0:
            self._state = BufferState.PARTIAL_MESSAGE
        else:
            self._state = BufferState.READY_FOR_MESSAGE

        return msg

    def peek_message(self) -> Optional[Message]:
        """Peeks at the next message without dequeuing it."""
        return self._completed_messages[0] if self._completed_messages else None

    # Outbound buffering (Messages to a Player)
    def enqueue_outbound(self, msg: Message) -> bool:
        if len(self._outbound_queue) >= self.max_queue_size:
            return False
        self._outbound_queue.append(msg)
        return True

    def flush_outbound(self) -> List[Message]:
        """Drains all outbound messages to send across socket/transport."""
        out = list(self._outbound_queue)
        self._outbound_queue.clear()
        return out

    def flush_and_reset(self) -> None:
        """Flushes all buffers upon player termination, disconnect, or error."""
        self._raw_stream_buffer.clear()
        self._completed_messages.clear()
        self._outbound_queue.clear()
        self._state = BufferState.READY_FOR_MESSAGE

    def get_status(self) -> dict:
        return {
            "player_id": self.player_id,
            "buffer_state": self._state.value,
            "raw_stream_bytes": len(self._raw_stream_buffer),
            "pending_inbound": len(self._completed_messages),
            "pending_outbound": len(self._outbound_queue),
            "dropped_count": self._dropped_message_count,
        }
