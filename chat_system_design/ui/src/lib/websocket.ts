import type { WSInboundEvent, WSOutboundEvent } from '../types/events';

interface WSOptions {
    userId: string;
    deviceId: string;
    roomId: string;
    onEvent: (payload: WSInboundEvent) => void;
    onStatus?: (s: 'connecting' | 'open' | 'closed' | 'reconnecting' | 'failed') => void;
    maxRetries?: number;
}

export function createWebSocket(opts: WSOptions) {
    const { userId, deviceId, roomId, onEvent, onStatus, maxRetries = 5 } = opts;
    let retries = 0;
    let ws: WebSocket;
    const connect = () => {
        onStatus?.(retries === 0 ? 'connecting' : 'reconnecting');
        ws = new WebSocket(`ws://localhost:8080/ws/${userId}/${deviceId}/${roomId}`);
        ws.addEventListener('open', () => {
            retries = 0;
            onStatus?.('open');
        });
        ws.addEventListener('close', (event) => {
            // Only reconnect if it's an abnormal closure (not code 1000)
            if (event.code !== 1000 && retries < maxRetries) {
                retries += 1;
                setTimeout(connect, 1000 * retries);
            } else {
                onStatus?.('closed');
            }
        });
        ws.addEventListener('message', (evt) => {
            try {
                onEvent(JSON.parse(evt.data));
            } catch {
                /* ignore */
            }
        });
    };
    connect();
    return {
        send: (obj: WSOutboundEvent) => {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
        },
        close: () => ws && ws.close(),
    };
}
