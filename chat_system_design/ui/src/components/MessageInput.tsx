import { useState, KeyboardEvent } from 'react';

interface Props {
    onSend: (text: string) => void;
    onTyping?: () => void;
}

export const MessageInput: React.FC<Props> = ({ onSend, onTyping }) => {
    const [value, setValue] = useState('');
    const send = () => {
        const v = value.trim();
        if (!v) return;
        onSend(v);
        setValue('');
    };
    const keyHandler = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
        else onTyping?.();
    };
    return (
        <div className="uk-flex uk-flex-middle" style={{ gap: 8 }}>
            <textarea className="uk-textarea" rows={2} placeholder="Type a message" value={value} onChange={e => setValue(e.target.value)} onKeyDown={keyHandler} />
            <button className="uk-button uk-button-primary" onClick={send}>Send</button>
        </div>
    );
};
