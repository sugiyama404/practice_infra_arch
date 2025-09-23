import { GetServerSideProps } from 'next';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useChatStore, usePresenceStore, useTypingStore } from '../../src/store/chatStore';
import { createWebSocket } from '../../src/lib/websocket';
import { fetchMessages, sendMessage } from '../../src/lib/api';
import { Sidebar } from '../../src/components/Sidebar';
import { MessageList } from '../../src/components/MessageList';
import { MessageInput } from '../../src/components/MessageInput';

interface ChatPageProps {
    initialRoomId: string;
    userId: string;
    deviceId: string;
}

export default function ChatPage({ initialRoomId, userId, deviceId }: ChatPageProps) {
    const router = useRouter();
    const roomId = (router.query.roomId as string) || initialRoomId;
    const { messages, addMessage, setMessages } = useChatStore();
    const { setPresence } = usePresenceStore();
    const { typingUsers, setTyping } = useTypingStore();
    const [content, setContent] = useState('');
    const wsRef = useRef<{ send: (o: any) => void; close: () => void } | null>(null);
    const [status, setStatus] = useState('connecting');
    const bottomRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        let aborted = false;
        fetchMessages({ user_id: userId, device_id: deviceId, room_id: roomId, last_message_id: 0 })
            .then(data => { if (!aborted) setMessages(data.messages); })
            .catch(console.error);
        return () => { aborted = true; };
    }, [roomId, userId, deviceId, setMessages]);

    useEffect(() => {
        const client = createWebSocket({
            userId, deviceId, roomId, onStatus: setStatus, onEvent: (payload) => {
                switch (payload.event) {
                    case 'message':
                        addMessage(payload.data);
                        break;
                    case 'presence':
                        setPresence(payload.data.user_id, { status: payload.data.status, last_seen: payload.data.last_seen });
                        break;
                    case 'typing':
                        setTyping(payload.data.user_id, !!payload.data.typing);
                        break;
                }
            }
        });
        wsRef.current = client;
        return () => client.close();
    }, [userId, deviceId, roomId, addMessage, setPresence, setTyping]);

    useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

    const handleSend = async () => {
        if (!content.trim()) return;
        const optimistic = { message_id: Date.now(), user_id: userId, room_id: roomId, content, timestamp: new Date().toISOString(), message_type: 'text', optimistic: true };
        addMessage(optimistic as any);
        setContent('');
        try {
            const res = await sendMessage({ user_id: userId, device_id: deviceId, room_id: roomId, content });
            addMessage({ ...res, user_id: userId, room_id: roomId, content, message_type: 'text' } as any);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="uk-flex uk-height-viewport">
            <Sidebar currentRoom={roomId} userId={userId} deviceId={deviceId} />
            <div className="uk-flex uk-flex-column uk-flex-1">
                <div className="uk-padding-small uk-box-shadow-small uk-background-default uk-flex uk-flex-middle uk-text-small" style={{ gap: 8 }}>
                    <span className="uk-text-bold">Room: {roomId}</span>
                    <span className="uk-badge">{status}</span>
                </div>
                <MessageList messages={messages} currentUser={userId} typingUsers={typingUsers} bottomRef={bottomRef} />
                <div className="uk-padding-small uk-background-muted uk-border-top">
                    <MessageInput onSend={(text) => {
                        const optimistic = { message_id: Date.now(), user_id: userId, room_id: roomId, content: text, timestamp: new Date().toISOString(), message_type: 'text', status: 'sending' } as any;
                        addMessage(optimistic);
                        sendMessage({ user_id: userId, device_id: deviceId, room_id: roomId, content: text })
                            .then(res => addMessage({ ...res, user_id: userId, room_id: roomId, content: text, message_type: 'text', status: 'sent' } as any))
                            .catch(() => {/* TODO: error toast */ });
                    }} onTyping={() => wsRef.current?.send({ event: 'typing', room_id: roomId, typing: true })} />
                </div>
            </div>
        </div>
    );
}

export const getServerSideProps: GetServerSideProps<ChatPageProps> = async (ctx) => {
    const { roomId } = ctx.query;
    const userId = (ctx.query.user_id as string) || 'alice';
    const deviceId = (ctx.query.device_id as string) || 'web';
    return { props: { initialRoomId: roomId as string, userId, deviceId } };
};
