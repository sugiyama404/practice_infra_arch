import { act } from 'react-dom/test-utils';
import { useChatStore } from './chatStore';
import type { ChatMessage } from '../types/message';

// Basic unit tests for chat store optimistic update & status transitions

describe('chatStore', () => {
  beforeEach(() => {
    // reset store state
    const { setMessages } = useChatStore.getState();
    setMessages([]);
  });

  const baseMsg = (over: Partial<ChatMessage>): ChatMessage => ({
    message_id: 1,
    user_id: 'u1',
    room_id: 'r1',
    content: 'hello',
    timestamp: new Date().toISOString(),
    message_type: 'text',
    ...over,
  });

  it('adds optimistic then real message merges instead of duplicate', () => {
    act(() => {
      useChatStore.getState().addMessage(baseMsg({ optimistic: true, status: 'sending' }));
      useChatStore.getState().addMessage(baseMsg({ optimistic: false, status: 'sent' }));
    });
    const { messages } = useChatStore.getState();
    expect(messages.length).toBe(1);
    expect(messages[0].status).toBe('sent');
    expect(messages[0].optimistic).toBeFalsy();
  });

  it('updateMessageStatus transitions sending->sent', () => {
    act(() => {
      useChatStore.getState().addMessage(baseMsg({ optimistic: true, status: 'sending' }));
      useChatStore.getState().updateMessageStatus(1, 'sent');
    });
    const msg = useChatStore.getState().messages[0];
    expect(msg.status).toBe('sent');
    expect(msg.optimistic).toBe(false);
  });

  it('addMessageReader appends reader and sets status read for author', () => {
    act(() => {
      useChatStore.getState().addMessage(baseMsg({ status: 'sent', optimistic: false }));
      useChatStore.getState().addMessageReader(1, 'otherUser', 'u1');
    });
    const msg = useChatStore.getState().messages[0];
    expect(msg.read_by).toContain('otherUser');
    expect(msg.status).toBe('read');
  });
});
