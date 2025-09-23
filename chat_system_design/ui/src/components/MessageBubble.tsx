import { ChatMessage } from '../types/message';
import { FaClock, FaCheck, FaCheckDouble } from 'react-icons/fa';
import clsx from 'clsx';

interface Props {
    message: ChatMessage;
    self: boolean;
}

export const MessageBubble: React.FC<Props> = ({ message, self }) => {
    const statusIcon = () => {
        switch (message.status) {
            case 'sending': return <FaClock className="uk-text-muted" size={10} />;
            case 'sent': return <FaCheck className="uk-text-primary" size={10} />;
            case 'read': return <FaCheckDouble className="uk-text-success" size={10} />;
            default: return null;
        }
    };
    return (
        <div className={clsx('uk-flex', self ? 'uk-flex-right' : 'uk-flex-left')}>
            <div className={clsx('uk-border-rounded uk-padding-small uk-width-auto uk-text-small', self ? 'uk-background-primary uk-light' : 'uk-background-default uk-box-shadow-small')} style={{ maxWidth: 320 }}>
                <div>{message.content}</div>
                <div className="uk-text-xxsmall uk-flex uk-flex-middle uk-flex-right uk-margin-small-top" style={{ gap: 4 }}>
                    <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                    {statusIcon()}
                </div>
            </div>
        </div>
    );
};
