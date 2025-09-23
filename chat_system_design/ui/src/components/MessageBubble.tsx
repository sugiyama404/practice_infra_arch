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
                return <FaClock className="uk-text-muted" size={10} />;
            case 'sent':
                return <FaCheck className="uk-text-primary" size={10} />;
            case 'read':
                return <FaCheckDouble className="uk-text-success" size={10} />;
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
                className="uk-button uk-button-text uk-text-warning uk-padding-small uk-margin-remove"
                onClick={() => onResend?.(message)}
                type="button"
            >
                <FaRedo size={10} />
            </button>
        );
    };
    return (
        <div className={clsx('uk-flex', self ? 'uk-flex-right' : 'uk-flex-left')}>
            <div
                className={clsx(
                    'uk-border-rounded uk-padding-small uk-width-auto uk-text-small',
                    self ? 'uk-background-primary uk-light' : 'uk-background-default uk-box-shadow-small',
                )}
                style={{ maxWidth: 320 }}
            >
                <div>{message.content}</div>
                <div
                    className="uk-text-xxsmall uk-flex uk-flex-middle uk-flex-right uk-margin-small-top"
                    style={{ gap: 6 }}
                >
                    <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                    {statusIcon()}
                    {resendIcon()}
                    {message.read_by && message.read_by.length > 0 && (
                        <div className="uk-inline">
                            <button
                                className="uk-button uk-button-text uk-text-muted uk-padding-small uk-margin-remove"
                                type="button"
                                uk-toggle="target: #read-by-dropdown-{message.message_id}"
                            >
                                <span className="uk-flex uk-flex-middle" style={{ gap: 2 }}>
                                    <FaUser size={9} />
                                    {message.read_by.length}
                                </span>
                            </button>
                            <div id={`read-by-dropdown-${message.message_id}`} uk-dropdown="mode: click">
                                <ul className="uk-nav uk-dropdown-nav">
                                    {message.read_by.map((user) => (
                                        <li key={user}>
                                            <a href="#">{user}</a>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
