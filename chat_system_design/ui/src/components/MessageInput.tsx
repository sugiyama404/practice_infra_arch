import { useState, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

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
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        } else onTyping?.();
    };
    return (
        <div className="flex items-end gap-3">
            <div className="flex-1 relative">
                <textarea
                    className="w-full resize-none rounded-2xl bg-slate-700 border border-slate-600 px-4 py-3 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all min-h-[44px] max-h-32"
                    rows={1}
                    placeholder="Type a message..."
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={keyHandler}
                    style={{ height: 'auto', minHeight: '44px' }}
                    onInput={(e) => {
                        const target = e.target as HTMLTextAreaElement;
                        target.style.height = 'auto';
                        target.style.height = Math.min(target.scrollHeight, 128) + 'px';
                    }}
                />
            </div>
            <button
                className="p-3 bg-gradient-accent rounded-full hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed hover-lift"
                onClick={send}
                disabled={!value.trim()}
            >
                <Send className="w-5 h-5 text-white" />
            </button>
        </div>
    );
};
