import { GetServerSideProps } from 'next';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useChatStore, usePresenceStore, useTypingStore } from '../../src/store/chatStore';
import { createWebSocket } from '../../src/lib/websocket';
import type { WSInboundEvent } from '../../src/types/events';
import { fetchMessages, sendMessage } from '../../src/lib/api';
import { notify, withErrorNotify } from '../../src/lib/notify';
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
    const {
        messages,
        addMessage,
        setMessages,
        updateMessageStatus,
        addMessageReader,
        addMessageReaders,
    } = useChatStore();
    const { setPresence } = usePresenceStore();
    const { typingUsers, setTyping } = useTypingStore();
    const wsRef = useRef<{ send: (o: any) => void; close: () => void } | null>(null);
    const [status, setStatus] = useState('connecting');
    const bottomRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        let aborted = false;
        const p = fetchMessages({
            user_id: userId,
            device_id: deviceId,
            room_id: roomId,
            last_message_id: 0,
        }).then((data) => {
            if (!aborted) setMessages(data.messages);
        });
        withErrorNotify(p, 'メッセージ取得に失敗しました');
        return () => {
            aborted = true;
        };
    }, [roomId, userId, deviceId, setMessages]);

    useEffect(() => {
        const client = createWebSocket({
            userId,
            deviceId,
            roomId,
            onStatus: setStatus,
            onEvent: (payload: WSInboundEvent) => {
                switch (payload.event) {
                    case 'message':
                        addMessage(payload.data);
                        break;
                    case 'ack':
                        if (payload.data.message_id) updateMessageStatus(payload.data.message_id, 'sent');
                        // Set sent_at for reliability indicator
                        const msg = messages.find((m) => m.message_id === payload.data.message_id);
                        if (msg) {
                            addMessage({ ...msg, sent_at: new Date().toISOString() });
                        }
                        break;
                    case 'read':
                        if (payload.data.message_id) {
                            addMessageReader(payload.data.message_id, payload.data.user_id, userId);
                        }
                        break;
                    case 'read_many':
                        addMessageReaders(payload.data.reads, userId);
                        break;
                    case 'presence':
                        setPresence(payload.data.user_id, {
                            status: payload.data.status,
                            last_seen: payload.data.last_seen,
                        });
                        break;
                    case 'typing':
                        setTyping(payload.data.user_id, !!payload.data.typing);
                        break;
                    case 'error':
                        notify.error(`Error: ${payload.data.message || 'unknown'}`);
                        break;
                }
            },
        });
        wsRef.current = client;
        return () => client.close();
    }, [userId, deviceId, roomId, addMessage, setPresence, setTyping, updateMessageStatus, addMessageReader, addMessageReaders, messages]); useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async (text: string) => {
        if (!text.trim()) return;
        const optimistic = {
            message_id: Date.now(),
            user_id: userId,
            room_id: roomId,
            content: text,
            timestamp: new Date().toISOString(),
            message_type: 'text',
            status: 'sending',
            optimistic: true,
        } as any;
        addMessage(optimistic);
        try {
            const res = await sendMessage({
                user_id: userId,
                device_id: deviceId,
                room_id: roomId,
                content: text,
            });
            addMessage({
                ...res,
                user_id: userId,
                room_id: roomId,
                content: text,
                message_type: 'text',
                status: 'sent',
            } as any);
        } catch (e) {
            notify.error('送信に失敗しました');
            // eslint-disable-next-line no-console
            console.error(e);
        }
    };

    return (
        <div className="uk-flex uk-height-viewport">
            <Sidebar currentRoom={roomId} userId={userId} deviceId={deviceId} />
            <div className="uk-flex uk-flex-column uk-flex-1">
                <div
                    className="uk-padding-small uk-box-shadow-small uk-background-default uk-flex uk-flex-middle uk-text-small"
                    style={{ gap: 8 }}
                >
                    <span className="uk-text-bold">Room: {roomId}</span>
                    <span className="uk-badge">{status}</span>
                </div>
                <MessageList
                    messages={messages}
                    currentUser={userId}
                    typingUsers={typingUsers}
                    bottomRef={bottomRef}
                    onResend={(msg) => handleSend(msg.content)}
                />
                <div className="uk-padding-small uk-background-muted uk-border-top">
                    <MessageInput
                        onSend={(text: string) => handleSend(text)}
                        onTyping={() => wsRef.current?.send({ event: 'typing', room_id: roomId, typing: true })}
                    />
                </div>
            </div>
        </div>
    );
}

export const getServerSideProps: GetServerSideProps<ChatPageProps> = async (ctx: any) => {
    const { roomId } = ctx.query;
    const userId = (ctx.query.user_id as string) || 'alice';
    const deviceId = (ctx.query.device_id as string) || 'web';
    return { props: { initialRoomId: roomId as string, userId, deviceId } };
};
