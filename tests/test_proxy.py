import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx
from cryptography.fernet import Fernet
from fastmcp import Client

from bridge import Bridge, Config, authorize_owner
from server import create_server


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []
        self.response = httpx.Response(200, json={"id": "message-123"})
        self.config = Config("http://waha:3000", "test-key", "123456@g.us",
                             state_dir=Path(self.temp.name))

        async def handle(request):
            self.calls.append(request)
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

        self.transport = httpx.MockTransport(handle)
        self.bridge = Bridge(self.config, self.transport)

    async def test_post_is_fixed_to_configured_chat(self):
        result = await self.bridge.post_update("Package shipped", "order:123:shipped")
        self.assertEqual(result["status"], "accepted")
        self.assertIn("not confirmed", result["note"])
        request = self.calls[0]
        self.assertEqual(str(request.url), "http://waha:3000/api/sendText")
        self.assertEqual(request.headers["X-Api-Key"], "test-key")
        self.assertEqual(json.loads(request.content)["chatId"], "123456@g.us")

    async def test_retry_after_restart_never_sends_twice(self):
        await self.bridge.post_update("Package shipped", "same-id")
        restarted = Bridge(self.config, self.transport)
        result = await restarted.post_update("Package shipped", "same-id")
        self.assertTrue(result["duplicate"])
        self.assertEqual(result["message_id"], "message-123")
        self.assertEqual(len(self.calls), 1)

    async def test_concurrent_retry_never_sends_twice(self):
        results = await asyncio.gather(*[
            self.bridge.post_update("Hello", "same-id") for _ in range(4)])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(sum(not r["duplicate"] for r in results), 1)

    async def test_request_id_cannot_be_reused_for_changed_text(self):
        await self.bridge.post_update("First", "same-id")
        with self.assertRaises(ValueError):
            await self.bridge.post_update("Different", "same-id")
        self.assertEqual(len(self.calls), 1)

    async def test_timeout_is_uncertain_and_not_retried(self):
        self.response = httpx.ReadTimeout("simulated timeout")
        first = await self.bridge.post_update("Hello", "uncertain-id")
        second = await self.bridge.post_update("Hello", "uncertain-id")
        self.assertEqual(first["status"], "unknown")
        self.assertEqual(second["status"], "unknown")
        self.assertEqual(len(self.calls), 1)

    async def test_redirect_does_not_leak_key_to_another_host(self):
        self.response = httpx.Response(307, headers={"Location": "https://other.example/"})
        result = await self.bridge.post_update("Hello", "redirect-id")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(len(self.calls), 1)

    async def test_read_is_bounded_and_removes_raw_engine_data(self):
        self.response = httpx.Response(200, json=[{
            "id": "m1", "body": "Hi", "participant": "111@c.us", "timestamp": 100,
            "fromMe": False, "_data": {"private": "secret"}, "hasMedia": True,
        }] * 4)
        result = await self.bridge.read_messages(limit=2, since=99)
        self.assertEqual(len(result["messages"]), 2)
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(self.calls[0].url.params["downloadMedia"], "false")
        self.assertEqual(self.calls[0].url.params["filter.timestamp.gte"], "99")
        self.assertIn("123456%40g.us", str(self.calls[0].url))

    async def test_bad_inputs_make_no_network_call(self):
        for text, key in [(" ", "id"), ("x" * 4001, "id"), ("Hi", "../bad")]:
            with self.assertRaises(ValueError):
                await self.bridge.post_update(text, key)
        for limit in [0, 51, True]:
            with self.assertRaises(ValueError):
                await self.bridge.read_messages(limit)
        self.assertEqual(self.calls, [])

    def test_owner_is_checked_by_numeric_identity(self):
        authorize_owner(SimpleNamespace(claims={"sub": "123456789"}), "123456789")
        for token in [None, SimpleNamespace(claims={"sub": "different", "login": "owner-name"})]:
            with self.assertRaises(PermissionError):
                authorize_owner(token, "123456789")


class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {
            "GITHUB_OWNER_ID": "123456789", "PUBLIC_URL": "https://relay.example.com",
            "GITHUB_CLIENT_ID": "test-client", "GITHUB_CLIENT_SECRET": "test-secret",
            "OAUTH_SIGNING_KEY": "x" * 64,
            "OAUTH_STORAGE_KEY": Fernet.generate_key().decode(),
            "WAHA_API_KEY": "test-waha-key", "WAHA_CHAT_ID": "123456@g.us",
            "STATE_DIR": self.temp.name,
        }
        self.calls = []

        async def handle(request):
            self.calls.append(request)
            return httpx.Response(200, json=[] if request.method == "GET" else {"id": "mcp-message"})

        self.bridge = Bridge(Config("http://waha:3000", "test-waha-key", "123456@g.us",
                                    state_dir=Path(self.temp.name)), httpx.MockTransport(handle))

    def make_server(self, token):
        return create_server(self.env, bridge_override=self.bridge, token_getter=lambda: token)

    async def test_mcp_discovers_exactly_two_tools_and_calls_them(self):
        mcp = self.make_server(SimpleNamespace(claims={"sub": "123456789"}))
        async with Client(mcp) as client:
            tools = await client.list_tools()
            self.assertEqual({t.name for t in tools}, {"read_messages", "post_update"})
            for tool in tools:
                self.assertNotIn("chat_id", tool.inputSchema["properties"])
            await client.call_tool("read_messages", {"limit": 3})
            await client.call_tool("post_update", {"text": "Test update", "request_id": "test:1"})
        self.assertEqual(len(self.calls), 2)

    async def test_authenticated_nonowner_cannot_read_or_post(self):
        for token in [None, SimpleNamespace(claims={"sub": "99"})]:
            async with Client(self.make_server(token)) as client:
                for name, args in [("read_messages", {}),
                                   ("post_update", {"text": "Hi", "request_id": "nope"})]:
                    with self.assertRaises(Exception) as caught:
                        await client.call_tool(name, args)
                    self.assertIn("not authorized", str(caught.exception))
        self.assertEqual(self.calls, [])

    async def test_http_rejects_anonymous_and_exposes_oauth_discovery(self):
        mcp = self.make_server(None)
        transport = httpx.ASGITransport(app=mcp.http_app())
        async with httpx.AsyncClient(transport=transport, base_url="https://relay.example.com") as client:
            response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(response.status_code, 401)
            self.assertIn("resource_metadata", response.headers["www-authenticate"])
            metadata = (await client.get("/.well-known/oauth-authorization-server")).json()
            self.assertIn("S256", metadata["code_challenge_methods_supported"])
            self.assertIn("registration_endpoint", metadata)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
