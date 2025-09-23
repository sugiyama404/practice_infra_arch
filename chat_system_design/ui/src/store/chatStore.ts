import { create } from 'zustand';
import type { ChatMessage } from '../types/message';

interface ChatState {
    messages: ChatMessage[];
    addMessage: (m: ChatMessage) => void;
    setMessages: (ms: ChatMessage[]) => void;
}

export const useChatStore = create<ChatState>((set) => ({
    messages: [],
    addMessage: (m: ChatMessage) => set((s: ChatState) => ({ messages: [...s.messages.filter((x: ChatMessage) => !(m.optimistic && x.optimistic && x.message_id === m.message_id)), m] })),
    setMessages: (ms: ChatMessage[]) => set(() => ({ messages: ms }))
}));

interface PresenceState {
    onlineUsers: Record<string, { status: 'online' | 'offline'; last_seen?: string }>;
    setPresence: (userId: string, data: { status: 'online' | 'offline'; last_seen?: string }) => void;
}

export const usePresenceStore = create<PresenceState>((set) => ({
    onlineUsers: {},
    setPresence: (userId: string, data: { status: 'online' | 'offline'; last_seen?: string }) => set((s: PresenceState) => ({ onlineUsers: { ...s.onlineUsers, [userId]: data } }))
}));

interface TypingState {
    typingUsers: Set<string>;
    setTyping: (userId: string, typing: boolean) => void;
}

export const useTypingStore = create<TypingState>((set) => ({
    typingUsers: new Set(),
    setTyping: (userId: string, typing: boolean) => set((s: TypingState) => {
        const next = new Set<string>(s.typingUsers);
        if (typing) next.add(userId); else next.delete(userId);
        return { typingUsers: next } as any;
    })
}));
