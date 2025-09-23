#!/usr/bin/env python3
"""
Chat System Test Client
使用方法:
1. docker-compose up でシステムを起動
2. python test_client.py でテスト実行
"""

import asyncio
import aiohttp
import websockets
import json

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080"


class ChatTestClient:
    def __init__(self, user_id: str, device_id: str):
        self.user_id = user_id
        self.device_id = device_id
        self.session = None
        self.ws = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

    async def send_message(self, room_id: str, content: str):
        """API経由でメッセージを送信"""
        url = f"{BASE_URL}/api/messages/send"
        data = {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "room_id": room_id,
            "content": content,
        }

        async with self.session.post(url, json=data) as response:
            result = await response.json()
            print(f"📤 [{self.user_id}] Sent message: {content}")
            print(f"   Response: {result}")
            return result

    async def sync_messages(self, room_id: str, last_message_id: int = 0):
        """差分同期APIでメッセージを取得"""
        url = f"{BASE_URL}/api/messages/sync"
        params = {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "room_id": room_id,
            "last_message_id": last_message_id,
        }

        async with self.session.get(url, params=params) as response:
            result = await response.json()
            print(f"🔄 [{self.user_id}] Synced messages from {last_message_id}")
            print(f"   Got {len(result.get('messages', []))} new messages")
            return result

    async def get_presence(self, target_user_id: str):
        """プレゼンス情報を取得"""
        url = f"{BASE_URL}/api/users/{target_user_id}/presence"

        async with self.session.get(url) as response:
            result = await response.json()
            print(f"👤 [{self.user_id}] Presence of {target_user_id}: {result}")
            return result

    async def connect_websocket(self, room_id: str):
        """WebSocket接続"""
        ws_url = f"{WS_URL}/ws/{self.user_id}/{self.device_id}/{room_id}"

        try:
            self.ws = await websockets.connect(ws_url)
            print(f"🔌 [{self.user_id}] Connected to WebSocket for room {room_id}")
            return True
        except Exception as e:
            print(f"❌ [{self.user_id}] WebSocket connection failed: {e}")
            return False

    async def listen_websocket(self):
        """WebSocketメッセージを受信"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                data = json.loads(message)
                if data.get("type") == "message":
                    print(
                        f"📨 [{self.user_id}] Received: {data['content']} from {data['user_id']}"
                    )
                elif data.get("type") == "typing":
                    typing_status = (
                        "typing..." if data.get("is_typing") else "stopped typing"
                    )
                    print(f"⌨️  [{self.user_id}] {data['user_id']} is {typing_status}")
                else:
                    print(f"🔔 [{self.user_id}] WebSocket message: {data}")
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 [{self.user_id}] WebSocket connection closed")
        except Exception as e:
            print(f"❌ [{self.user_id}] WebSocket error: {e}")

    async def send_typing_indicator(self, is_typing: bool = True):
        """タイピングインジケーターを送信"""
        if self.ws:
            message = {"type": "typing", "is_typing": is_typing}
            await self.ws.send(json.dumps(message))

    async def ping_websocket(self):
        """WebSocketのping/pong"""
        if self.ws:
            await self.ws.send(json.dumps({"type": "ping"}))


async def test_basic_flow():
    """基本的なチャットフローのテスト"""
    print("=" * 60)
    print("🚀 Basic Chat Flow Test")
    print("=" * 60)

    # 2つのクライアントを作成
    async with (
        ChatTestClient("user1", "device1") as client1,
        ChatTestClient("user2", "device3") as client2,
    ):
        room_id = "room1"

        # WebSocket接続
        await client1.connect_websocket(room_id)
        await client2.connect_websocket(room_id)

        # WebSocketリスナーを開始
        listener1_task = asyncio.create_task(client1.listen_websocket())
        listener2_task = asyncio.create_task(client2.listen_websocket())

        await asyncio.sleep(1)  # 接続安定化

        # プレゼンス確認
        await client1.get_presence("user2")
        await client2.get_presence("user1")

        # メッセージ送信テスト
        await client1.send_message(room_id, "Hello from Alice! 👋")
        await asyncio.sleep(2)

        await client2.send_message(room_id, "Hi Alice! How are you? 😊")
        await asyncio.sleep(2)

        # タイピングインジケーターテスト
        print("\n📝 Testing typing indicators...")
        await client1.send_typing_indicator(True)
        await asyncio.sleep(2)
        await client1.send_typing_indicator(False)
        await asyncio.sleep(1)

        # より多くのメッセージ
        await client1.send_message(room_id, "I'm testing the chat system!")
        await asyncio.sleep(1)
        await client2.send_message(room_id, "That's great! Everything works fine.")
        await asyncio.sleep(2)

        # 差分同期テスト
        print("\n🔄 Testing message sync...")
        sync_result = await client1.sync_messages(room_id, 0)
        print(f"   Synced {len(sync_result.get('messages', []))} messages")

        # テスト終了
        listener1_task.cancel()
        listener2_task.cancel()

        print("\n✅ Basic flow test completed!")


async def test_multi_device_sync():
    """マルチデバイス同期テスト"""
    print("\n" + "=" * 60)
    print("📱 Multi-Device Sync Test")
    print("=" * 60)

    # 同一ユーザーの複数デバイス
    async with (
        ChatTestClient("user1", "device1") as phone,
        ChatTestClient("user1", "device2") as tablet,
    ):
        room_id = "room2"

        # 両デバイスでWebSocket接続
        await phone.connect_websocket(room_id)
        await tablet.connect_websocket(room_id)

        listener_phone = asyncio.create_task(phone.listen_websocket())
        listener_tablet = asyncio.create_task(tablet.listen_websocket())

        await asyncio.sleep(1)

        # 一方のデバイスからメッセージ送信
        await phone.send_message(room_id, "Message from phone 📱")
        await asyncio.sleep(2)

        await tablet.send_message(room_id, "Message from tablet 📟")
        await asyncio.sleep(2)

        # 差分同期確認
        phone_sync = await phone.sync_messages(room_id, 0)
        tablet_sync = await tablet.sync_messages(room_id, 0)

        print(f"📱 Phone synced: {phone_sync.get('cur_max_message_id', 0)} messages")
        print(f"📟 Tablet synced: {tablet_sync.get('cur_max_message_id', 0)} messages")

        listener_phone.cancel()
        listener_tablet.cancel()

        print("\n✅ Multi-device sync test completed!")


async def test_offline_scenario():
    """オフライン/オンラインシナリオテスト"""
    print("\n" + "=" * 60)
    print("🔄 Offline/Online Scenario Test")
    print("=" * 60)

    async with ChatTestClient("user3", "device4") as client:
        room_id = "room3"

        # メッセージを送信（オフライン中に他のユーザーが送信したと仮定）
        print("📤 Sending messages while user is 'offline'...")

        # 別のクライアントからメッセージ送信
        async with ChatTestClient("user2", "device3") as sender:
            await sender.send_message(room_id, "Message while user3 was offline 1")
            await sender.send_message(room_id, "Message while user3 was offline 2")
            await sender.send_message(room_id, "Message while user3 was offline 3")

        await asyncio.sleep(1)

        # 「オンライン」になって差分同期
        print("\n🔌 User coming online and syncing...")
        sync_result = await client.sync_messages(room_id, 0)

        print(f"📨 Synced {len(sync_result.get('messages', []))} messages")
        for msg in sync_result.get("messages", []):
            print(f"   - {msg['user_id']}: {msg['content']}")

        print("\n✅ Offline/online scenario test completed!")


async def main():
    """メインテスト関数"""
    print("🧪 Chat System Integration Test")
    print("Please ensure docker-compose is running with all services")

    # サービスが起動するまで待機
    print("\n⏳ Waiting for services to start...")
    await asyncio.sleep(5)

    try:
        # 基本フローテスト
        await test_basic_flow()

        # マルチデバイステスト
        await test_multi_device_sync()

        # オフライン/オンラインテスト
        await test_offline_scenario()

        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
