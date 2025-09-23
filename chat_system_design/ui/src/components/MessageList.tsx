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
        <div
            className="uk-flex-1 uk-overflow-auto uk-padding-small uk-flex uk-flex-column"
            style={{ rowGap: 8 }}
        >
            {messages.map((m) => (
                <MessageBubble
                    key={m.message_id + String(m.optimistic || '')}
                    message={m}
                    self={m.user_id === currentUser}
                    onResend={onResend}
                />
            ))}
            {typingUsers.size > 0 && (
                <div className="uk-text-meta">{Array.from(typingUsers).join(', ')} is typing...</div>
            )}
            <div ref={bottomRef} />
        </div>
    );
};
