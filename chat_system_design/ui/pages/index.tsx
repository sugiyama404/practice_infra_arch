import Link from 'next/link';
import { useState } from 'react';
import { MessageSquare, Users, Settings } from 'lucide-react';

export default function Home() {
    const [roomId, setRoomId] = useState('room1');
    const [userId, setUserId] = useState('alice');
    const [deviceId, setDeviceId] = useState('web');

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
            <div className="glass rounded-2xl p-8 w-full max-w-md hover-lift">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-accent rounded-full mb-4">
                        <MessageSquare className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Chat Demo</h1>
                    <p className="text-slate-300">Enter your chat room</p>
                </div>

                <div className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Room ID</label>
                        <input
                            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                            value={roomId}
                            onChange={(e) => setRoomId(e.target.value)}
                            placeholder="Enter room ID"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">User ID</label>
                        <input
                            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            placeholder="Enter user ID"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Device ID</label>
                        <input
                            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                            value={deviceId}
                            onChange={(e) => setDeviceId(e.target.value)}
                            placeholder="Enter device ID"
                        />
                    </div>

                    <Link
                        className="w-full bg-gradient-accent text-white font-semibold py-3 px-6 rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 hover-lift"
                        href={`/chat/${roomId}?user_id=${userId}&device_id=${deviceId}`}
                    >
                        <MessageSquare className="w-5 h-5" />
                        Enter Chat
                    </Link>
                </div>
            </div>
        </div>
    );
}
