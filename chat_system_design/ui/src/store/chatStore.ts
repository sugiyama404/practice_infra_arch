import { create } from 'zustand';
import type { ChatMessage } from '../types/message';

interface ChatState {
    messages: ChatMessage[];
    addMessage: (m: ChatMessage) => void;
    setMessages: (ms: ChatMessage[]) => void;
    updateMessageStatus: (id: number, status: NonNullable<ChatMessage['status']>) => void;
}

export const useChatStore = create<ChatState>(
    (set: (fn: (state: ChatState) => Partial<ChatState>) => void | ChatState) => ({
        messages: [],
        addMessage: (m: ChatMessage) =>
            set((s: ChatState) => {
                // if message with same id exists update instead of append (e.g. optimistic -> real)
                const existingIdx = s.messages.findIndex((msg) => msg.message_id === m.message_id);
                if (existingIdx >= 0) {
                    const clone = [...s.messages];
                    clone[existingIdx] = { ...clone[existingIdx], ...m, optimistic: false };
                    return { messages: clone };
                }
                return {
                    messages: [
                        ...s.messages.filter(
                            (x: ChatMessage) => !(m.optimistic && x.optimistic && x.message_id === m.message_id),
                        ),
                        m,
                    ],
                };
            }),
        setMessages: (ms: ChatMessage[]) => set(() => ({ messages: ms })),
        updateMessageStatus: (id: number, status: NonNullable<ChatMessage['status']>) =>
            set((s: ChatState) => ({
                messages: s.messages.map((m) =>
                    m.message_id === id ? { ...m, status, optimistic: false } : m,
                ),
            })),
    }),
);

interface PresenceState {
    onlineUsers: Record<string, { status: 'online' | 'offline'; last_seen?: string }>;
    setPresence: (userId: string, data: { status: 'online' | 'offline'; last_seen?: string }) => void;
}

export const usePresenceStore = create<PresenceState>(
    (set: (fn: (state: PresenceState) => Partial<PresenceState>) => void | PresenceState) => ({
        onlineUsers: {},
        setPresence: (userId: string, data: { status: 'online' | 'offline'; last_seen?: string }) =>
            set((s: PresenceState) => ({ onlineUsers: { ...s.onlineUsers, [userId]: data } })),
    }),
);

interface TypingState {
    typingUsers: Set<string>;
    setTyping: (userId: string, typing: boolean) => void;
}

// keep timers to auto clear
const typingTimers: Record<string, any> = {};

export const useTypingStore = create<TypingState>(
    (set: (fn: (state: TypingState) => Partial<TypingState>) => void | TypingState) => ({
        typingUsers: new Set<string>(),
        setTyping: (userId: string, typing: boolean) =>
            set((s: TypingState) => {
                const next = new Set<string>(s.typingUsers);
                if (typing) {
                    next.add(userId);
                    if (typingTimers[userId]) clearTimeout(typingTimers[userId]);
                    typingTimers[userId] = setTimeout(() => {
                        set((cur: TypingState) => {
                            const nn = new Set<string>(cur.typingUsers);
                            nn.delete(userId);
                            return { typingUsers: nn };
                        });
                    }, 3000); // auto clear after 3s
                } else {
                    next.delete(userId);
                    if (typingTimers[userId]) {
                        clearTimeout(typingTimers[userId]);
                        delete typingTimers[userId];
                    }
                }
                return { typingUsers: next };
            }),
    }),
);
