import Link from 'next/link';
import { useState } from 'react';

export default function Home() {
  const [roomId, setRoomId] = useState('room1');
  const [userId, setUserId] = useState('alice');
  const [deviceId, setDeviceId] = useState('web');
  return (
    <div className="h-screen flex flex-col">
      <header className="p-4 shadow bg-white font-semibold">Chat Demo</header>
      <main className="flex-1 p-4 space-y-4 max-w-xl mx-auto w-full">
        <div className="space-y-2">
          <label className="block text-sm font-medium">Room ID</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">User ID</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Device ID</label>
          <input
            className="border rounded px-2 py-1 w-full"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
          />
        </div>
        <Link
          className="inline-block bg-blue-600 text-white px-4 py-2 rounded"
          href={`/chat/${roomId}?user_id=${userId}&device_id=${deviceId}`}
        >
          Enter Chat
        </Link>
      </main>
    </div>
  );
}
