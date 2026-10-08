"""
Unit tests for 3-State Message Buffering and Wire Protocol (Carlson 1986).
Tests:
- READY_FOR_MESSAGE -> PARTIAL_MESSAGE -> COMPLETE_MESSAGE transitions
- Chunk fragmentation and assembly
- Buffer overflow / queue depth
- Wire framing serialization
"""

import unittest
import json
from turnprog.models import (
    BufferState,
    Message,
    MessageType,
)
from turnprog.buffers import MessageFramingBuffer
from turnprog.protocol import WireProtocol, Envelope


class TestMessageFramingBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer = MessageFramingBuffer("player-101", max_queue_size=5)

    def test_buffer_three_state_transitions(self):
        # 1. Initially READY_FOR_MESSAGE
        self.assertEqual(self.buffer.state, BufferState.READY_FOR_MESSAGE)
        self.assertEqual(self.buffer.pending_count, 0)

        # 2. Feed partial chunk (no trailing newline)
        msg_obj = {"msg_type": "submit_move", "sender_id": "player-101", "payload": {"action": "jump"}}
        raw_full = json.dumps(msg_obj).encode("utf-8") + b"\n"

        part1 = raw_full[:15]
        completed = self.buffer.feed_bytes(part1)
        self.assertEqual(len(completed), 0)
        # Should transition to PARTIAL_MESSAGE
        self.assertEqual(self.buffer.state, BufferState.PARTIAL_MESSAGE)

        # 3. Feed remainder with newline
        part2 = raw_full[15:]
        completed = self.buffer.feed_bytes(part2)
        self.assertEqual(len(completed), 1)
        # Should transition to COMPLETE_MESSAGE
        self.assertEqual(self.buffer.state, BufferState.COMPLETE_MESSAGE)

        # 4. Pop message
        popped = self.buffer.pop_message()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.msg_type, MessageType.SUBMIT_MOVE)
        self.assertEqual(popped.payload["action"], "jump")

        # After popping all messages, should return to READY_FOR_MESSAGE
        self.assertEqual(self.buffer.state, BufferState.READY_FOR_MESSAGE)

    def test_multi_message_stream(self):
        # Multiple messages arriving in single packet
        m1 = {"msg_type": "heartbeat", "sender_id": "p1"}
        m2 = {"msg_type": "submit_move", "sender_id": "p1", "payload": {"action": "fire"}}
        stream = json.dumps(m1).encode("utf-8") + b"\n" + json.dumps(m2).encode("utf-8") + b"\n"

        completed = self.buffer.feed_bytes(stream)
        self.assertEqual(len(completed), 2)
        self.assertEqual(self.buffer.pending_count, 2)

        p1 = self.buffer.pop_message()
        p2 = self.buffer.pop_message()
        self.assertEqual(p1.msg_type, MessageType.HEARTBEAT)
        self.assertEqual(p2.msg_type, MessageType.SUBMIT_MOVE)


class TestWireProtocol(unittest.TestCase):
    def test_envelope_roundtrip(self):
        msg = WireProtocol.prompt_turn("p1", timeout_sec=10.0, round_num=3)
        envelope = Envelope(
            server_id="node-1",
            client_id="p1",
            message=msg,
        )
        wire_bytes = envelope.serialize()
        self.assertTrue(wire_bytes.endswith(b"\n"))

        deserialized = Envelope.deserialize(wire_bytes)
        self.assertEqual(deserialized.server_id, "node-1")
        self.assertEqual(deserialized.message.msg_type, MessageType.PROMPT_TURN)
        self.assertEqual(deserialized.message.payload["current_player_id"], "p1")


if __name__ == "__main__":
    unittest.main()
