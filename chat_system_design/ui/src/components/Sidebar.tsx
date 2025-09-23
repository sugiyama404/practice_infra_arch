import Link from 'next/link';
import { useRouter } from 'next/router';
import { usePresenceStore } from '../store/chatStore';
import { useEffect, useState } from 'react';
import { Hash, Users, X, Search, Settings, User } from 'lucide-react';

interface SidebarProps {
    currentRoom: string;
    userId: string;
    deviceId: string;
    onToggle?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentRoom, userId, deviceId, onToggle }) => {
    // 仮のチャンネル一覧（本来はAPIで取得）
    const channels = ['room1', 'room2', 'room3'];
    const { onlineUsers } = usePresenceStore();
    const router = useRouter();
    const [tab, setTab] = useState<'channels' | 'dm'>('channels');

    useEffect(() => {
        /* could sync presence */
    }, []);

    return (
        <div className="h-full bg-slate-800 text-slate-100 flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-slate-700">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Chat UI</h2>
                    <button
                        onClick={onToggle}
                        className="lg:hidden p-2 rounded-lg hover:bg-slate-700 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* User info */}
                <div className="flex items-center gap-3 p-3 bg-slate-700/50 rounded-lg">
                    <div className="w-8 h-8 bg-gradient-accent rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{userId}</div>
                        <div className="text-xs text-slate-400">dev:{deviceId}</div>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-700">
                <button
                    onClick={() => setTab('channels')}
                    className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${tab === 'channels'
                            ? 'text-purple-400 border-b-2 border-purple-400'
                            : 'text-slate-400 hover:text-slate-300'
                        }`}
                >
                    Channels
                </button>
                <button
                    onClick={() => setTab('dm')}
                    className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${tab === 'dm'
                            ? 'text-purple-400 border-b-2 border-purple-400'
                            : 'text-slate-400 hover:text-slate-300'
                        }`}
                >
                    DM
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                {tab === 'channels' && (
                    <div>
                        <div className="mb-4">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <input
                                    type="text"
                                    placeholder="Search channels..."
                                    className="w-full pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            {channels.map((c) => (
                                <button
                                    key={c}
                                    onClick={() => {
                                        onToggle?.();
                                        router.push(`/chat/${c}?user_id=${userId}&device_id=${deviceId}`);
                                    }}
                                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors hover:bg-slate-700 ${c === currentRoom ? 'bg-purple-600 text-white' : 'text-slate-300'
                                        }`}
                                >
                                    <div className="flex items-center gap-2">
                                        <Hash className="w-4 h-4" />
                                        <span className="text-sm">{c}</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {tab === 'dm' && (
                    <div className="text-center text-slate-400 py-8">
                        <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p className="text-sm">DM not implemented</p>
                    </div>
                )}

                {/* Online Users */}
                <div className="mt-6 pt-4 border-t border-slate-700">
                    <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                        Online Users
                    </h3>
                    <div className="space-y-2">
                        {Object.entries(onlineUsers).map(([uid, info]) => (
                            <div
                                key={uid}
                                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-700/50 transition-colors"
                            >
                                <div
                                    className={`w-2 h-2 rounded-full ${info.status === 'online' ? 'bg-green-400 pulse' : 'bg-slate-500'}`}
                                ></div>
                                <span className="text-sm text-slate-300 truncate">{uid}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-700">
                <button className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-slate-700 transition-colors">
                    <Settings className="w-5 h-5 text-slate-400" />
                    <span className="text-sm text-slate-300">Settings</span>
                </button>
            </div>
        </div>
    );
};
