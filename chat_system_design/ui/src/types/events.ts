import type { ChatMessage } from './message';

// Inbound events coming from the server -> client
export interface MessageEventPayload {
    event: 'message';
    data: ChatMessage;
}

export interface AckEventPayload {
    event: 'ack';
    data: { message_id: number };
}

export interface ReadEventPayload {
    event: 'read';
    data: { message_id: number; user_id: string };
}

export interface ReadManyEventPayload {
    event: 'read_many';
    data: { reads: { message_id: number; user_id: string }[] };
}

export interface PresenceEventPayload {
    event: 'presence';
    data: { user_id: string; status: 'online' | 'offline'; last_seen?: string };
}

export interface TypingEventPayload {
    event: 'typing';
    data: { user_id: string; typing: boolean };
}

export interface ErrorEventPayload {
    event: 'error';
    data: { message?: string };
}

export type WSInboundEvent =
    | MessageEventPayload
    | AckEventPayload
    | ReadEventPayload
    | ReadManyEventPayload
    | PresenceEventPayload
    | TypingEventPayload
    | ErrorEventPayload;

// Outbound events (client -> server) we currently emit
export interface OutboundTypingEvent {
    event: 'typing';
    room_id: string;
    typing: boolean;
}

export type WSOutboundEvent = OutboundTypingEvent;
