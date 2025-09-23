import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export interface SendMessageRequest { user_id: string; device_id: string; room_id: string; content: string; }
export interface SendMessageResponse { message_id: number; status: string; timestamp: string; }

export async function sendMessage(body: SendMessageRequest): Promise<SendMessageResponse> {
    const res = await axios.post(`${BASE}/api/messages/send`, body);
    return res.data;
}

export interface FetchMessagesParams { user_id: string; device_id: string; room_id: string; last_message_id?: number; limit?: number; }
export interface ChatMessage { message_id: number; user_id: string; room_id: string; content: string; timestamp: string; message_type: string; optimistic?: boolean; }
export interface FetchMessagesResponse { messages: ChatMessage[]; cur_max_message_id: number; has_more: boolean; }

export async function fetchMessages(params: FetchMessagesParams): Promise<FetchMessagesResponse> {
    const res = await axios.get(`${BASE}/api/messages/sync`, { params });
    return res.data;
}
