export interface ChatMessage {
    message_id: number;
    user_id: string;
    room_id: string;
    content: string;
    timestamp: string;
    message_type: string;
    optimistic?: boolean;
    status?: 'sending' | 'sent' | 'read';
    read_by?: string[];
    sent_at?: string; // for reliability indicator
}
