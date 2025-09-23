import { ChatMessage } from '../types/message';
import { MessageBubble } from './MessageBubble';

interface Props {
    messages: ChatMessage[];
    currentUser: string;
    typingUsers: Set<string>;
    bottomRef: React.RefObject<HTMLDivElement>;
    onResend?: (message: ChatMessage) => void;
}

export const MessageList: React.FC<Props> = ({
    messages,
    currentUser,
    typingUsers,
    bottomRef,
    onResend,
}) => {
    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => (
                <MessageBubble
                    key={m.message_id + String(m.optimistic || '')}
                    message={m}
                    self={m.user_id === currentUser}
                    onResend={onResend}
                />
            ))}
            {typingUsers.size > 0 && (
                <div className="text-slate-400 text-sm italic">
                    {Array.from(typingUsers).join(', ')} is typing...
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    );
};
