import Link from 'next/link';
import { useRouter } from 'next/router';
import { usePresenceStore } from '../store/chatStore';
import { useEffect, useState } from 'react';

interface SidebarProps {
  currentRoom: string;
  userId: string;
  deviceId: string;
  onChangeRoom?: (room: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentRoom,
  userId,
  deviceId,
  onChangeRoom,
}) => {
  // 仮のチャンネル一覧（本来はAPIで取得）
  const channels = ['room1', 'room2', 'room3'];
  const { onlineUsers } = usePresenceStore();
  const router = useRouter();
  const [tab, setTab] = useState<'channels' | 'dm'>('channels');
  useEffect(() => {
    /* could sync presence */
  }, []);
  return (
    <div
      className="uk-flex uk-flex-column uk-height-1-1 uk-background-muted"
      style={{ width: 240 }}
    >
      <div className="uk-padding-small uk-text-small uk-text-bold">Chat UI</div>
      <div className="uk-flex uk-flex-middle uk-padding-small uk-grid-small" data-uk-grid>
        <div>
          <span className="uk-label">{userId}</span>
        </div>
        <div className="uk-text-meta">dev:{deviceId}</div>
      </div>
      <ul className="uk-tab uk-tab-left" style={{ marginBottom: 0 }}>
        <li className={tab === 'channels' ? 'uk-active' : ''}>
          <a onClick={() => setTab('channels')}>Channels</a>
        </li>
        <li className={tab === 'dm' ? 'uk-active' : ''}>
          <a onClick={() => setTab('dm')}>DM</a>
        </li>
      </ul>
      <div className="uk-overflow-auto uk-flex-1 uk-padding-small">
        {tab === 'channels' && (
          <ul className="uk-nav uk-nav-default">
            {channels.map((c) => (
              <li key={c} className={c === currentRoom ? 'uk-active' : ''}>
                <a
                  onClick={() => {
                    onChangeRoom?.(c);
                    router.push(`/chat/${c}?user_id=${userId}&device_id=${deviceId}`);
                  }}
                >
                  # {c}
                </a>
              </li>
            ))}
          </ul>
        )}
        {tab === 'dm' && <div className="uk-text-meta">(DM not implemented)</div>}
        <hr />
        <div className="uk-text-small uk-text-bold">Online Users</div>
        <ul className="uk-list uk-list-collapse uk-text-small">
          {Object.entries(onlineUsers).map(([uid, info]) => (
            <li key={uid} className="uk-flex uk-flex-middle uk-grid-small" data-uk-grid>
              <div
                style={{ width: 10, height: 10 }}
                className={`uk-border-circle ${info.status === 'online' ? 'uk-background-success' : 'uk-background-secondary'}`}
              />
              <div>{uid}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
