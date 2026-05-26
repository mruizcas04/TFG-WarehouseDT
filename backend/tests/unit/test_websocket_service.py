"""
Unit tests for the in-process WebSocket service (app/services/websocket_service.py).

The service is a thin fan-out: it keeps a list of accepted connections and
broadcasts JSON payloads to all of them, removing any connection whose send
raises. The tests use AsyncMock WebSocket stand-ins so we don't need a real
ASGI transport.

Pattern: Arrange → Act → Assert
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.services.websocket_service import WebSocketService


def _ws_mock():
    """Fake WebSocket exposing accept() and send_text() as AsyncMock."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestConnect:

    async def test_connect_accepts_and_registers(self):
        svc = WebSocketService()
        ws = _ws_mock()

        await svc.connect(ws)

        ws.accept.assert_awaited_once()
        assert ws in svc.active_connections

    def test_disconnect_removes_known_connection(self):
        svc = WebSocketService()
        ws = _ws_mock()
        svc.active_connections.append(ws)

        svc.disconnect(ws)

        assert ws not in svc.active_connections

    def test_disconnect_ignores_unknown_connection(self):
        """Disconnecting a connection that isn't registered must be a no-op."""
        svc = WebSocketService()
        ws = _ws_mock()
        # Not in active_connections
        svc.disconnect(ws)  # should not raise
        assert svc.active_connections == []


class TestBroadcast:

    async def test_broadcast_sends_to_all_connections(self):
        svc = WebSocketService()
        ws1, ws2 = _ws_mock(), _ws_mock()
        svc.active_connections = [ws1, ws2]

        await svc.broadcast("hello", {"foo": "bar"})

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()
        # Payload is well-formed JSON with event + data
        payload = json.loads(ws1.send_text.call_args[0][0])
        assert payload == {"event": "hello", "data": {"foo": "bar"}}

    async def test_broadcast_removes_failing_connection(self):
        """A connection whose send_text raises is removed from active_connections."""
        svc = WebSocketService()
        good = _ws_mock()
        bad = _ws_mock()
        bad.send_text.side_effect = RuntimeError("connection lost")
        svc.active_connections = [good, bad]

        await svc.broadcast("ping", {})

        assert bad not in svc.active_connections
        assert good in svc.active_connections


class TestBroadcastHelpers:

    async def test_broadcast_inventory_updated_includes_location(self):
        svc = WebSocketService()
        ws = _ws_mock()
        svc.active_connections = [ws]

        await svc.broadcast_inventory_updated("loc-1", {"quantity": 3})

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["event"] == "inventory_updated"
        assert payload["data"]["location_id"] == "loc-1"
        assert payload["data"]["quantity"] == 3

    async def test_broadcast_movement_created_carries_inventories(self):
        svc = WebSocketService()
        ws = _ws_mock()
        svc.active_connections = [ws]

        await svc.broadcast_movement_created(
            movement_id="mov-1",
            data={"type": "entrada"},
            origin_inventory=None,
            destination_inventory={"id": "i-1"},
        )

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["event"] == "movement_created"
        assert payload["data"]["movement_id"] == "mov-1"
        assert payload["data"]["destination_inventory"] == {"id": "i-1"}
        assert payload["data"]["origin_inventory"] is None

    async def test_broadcast_task_assigned_includes_locations(self):
        svc = WebSocketService()
        ws = _ws_mock()
        svc.active_connections = [ws]

        await svc.broadcast_task_assigned(
            task_id="t-1",
            assigned_to="u-1",
            origin_location_id=None,
            destination_location_id="loc-9",
        )

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["event"] == "task_assigned"
        assert payload["data"]["task_id"] == "t-1"
        assert payload["data"]["destination_location_id"] == "loc-9"

    async def test_broadcast_task_status_changed_carries_status_and_locations(self):
        svc = WebSocketService()
        ws = _ws_mock()
        svc.active_connections = [ws]

        await svc.broadcast_task_status_changed(
            task_id="t-2",
            status="completada",
            origin_location_id="loc-A",
            destination_location_id="loc-B",
        )

        payload = json.loads(ws.send_text.call_args[0][0])
        assert payload["event"] == "task_status_changed"
        assert payload["data"]["status"] == "completada"
        assert payload["data"]["origin_location_id"] == "loc-A"
        assert payload["data"]["destination_location_id"] == "loc-B"
