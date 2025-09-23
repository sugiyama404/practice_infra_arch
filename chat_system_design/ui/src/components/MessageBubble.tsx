import { ChatMessage } from '../types/message';
import { FaClock, FaCheck, FaCheckDouble, FaUser, FaRedo } from 'react-icons/fa';
import clsx from 'clsx';

interface Props {
    message: ChatMessage;
    self: boolean;
    onResend?: (message: ChatMessage) => void;
}

export const MessageBubble: React.FC<Props> = ({ message, self, onResend }) => {
    const statusIcon = () => {
        switch (message.status) {
            case 'sending':
                return <FaClock className="w-3 h-3 text-slate-400" />;
            case 'sent':
                return <FaCheck className="w-3 h-3 text-slate-400" />;
            case 'read':
                return <FaCheckDouble className="w-3 h-3 text-green-400" />;
            default:
                return null;
        }
    };

    const resendIcon = () => {
        if (!self || message.status !== 'sent' || !message.sent_at) return null;
        const sentTime = new Date(message.sent_at).getTime();
        const now = Date.now();
        if (now - sentTime < 5000) return null; // 5 seconds
        return (
            <button
                className="p-1 rounded hover:bg-slate-700 transition-colors"
                onClick={() => onResend?.(message)}
                type="button"
            >
                <FaRedo className="w-3 h-3 text-orange-400" />
            </button>
        );
    };

    return (
        <div className={clsx('flex', self ? 'justify-end' : 'justify-start')}>
            <div
                className={clsx(
                    'max-w-xs lg:max-w-md px-4 py-2 rounded-2xl text-sm',
                    self
                        ? 'bg-gradient-accent text-white rounded-br-md'
                        : 'bg-slate-700 text-slate-100 rounded-bl-md',
                )}
            >
                <div>{message.content}</div>
                <div className="flex items-center justify-end gap-1 mt-1 text-xs text-slate-300">
                    <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                    {statusIcon()}
                    {resendIcon()}
                    {message.read_by && message.read_by.length > 0 && (
                        <div className="relative">
                            <button
                                className="p-1 rounded hover:bg-slate-600 transition-colors"
                                type="button"
                                title={`Read by: ${message.read_by.join(', ')}`}
                            >
                                <FaUser className="w-3 h-3" />
                                <span className="ml-1">{message.read_by.length}</span>
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
