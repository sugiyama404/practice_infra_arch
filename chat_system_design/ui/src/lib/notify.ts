// Unified notification utility wrapping UIkit.notification with graceful fallbacks.

export type NotifyStatus = 'primary' | 'success' | 'warning' | 'danger' | 'info';

interface NotifyOptions {
  status?: NotifyStatus;
  timeout?: number; // ms
  pos?: string; // e.g. 'top-right'
}

// Track recent notifications to prevent duplicates
const recentNotifications = new Map<string, number>();
const DUPLICATE_WINDOW = 3000; // 3 seconds

function core(message: string, opts: NotifyOptions = {}) {
  const key = `${opts.status || 'primary'}:${message}`;
  const now = Date.now();
  const lastShown = recentNotifications.get(key);
  if (lastShown && now - lastShown < DUPLICATE_WINDOW) {
    return; // Skip duplicate
  }
  recentNotifications.set(key, now);
  // Clean up old entries
  for (const [k, t] of recentNotifications) {
    if (now - t > DUPLICATE_WINDOW) {
      recentNotifications.delete(k);
    }
  }

  if (typeof window !== 'undefined' && (window as any).UIkit?.notification) {
    (window as any).UIkit.notification({
      message,
      status: opts.status || 'primary',
      timeout: opts.timeout ?? 3000,
      pos: opts.pos || 'top-right',
    });
  } else {
    // Fallback: console output (dev container / SSR)
    // eslint-disable-next-line no-console
    console.log(`[notify:${opts.status || 'primary'}] ${message}`);
  }
}

export const notify = {
  raw: core,
  success: (msg: string, opts?: Omit<NotifyOptions, 'status'>) =>
    core(msg, { ...opts, status: 'success' }),
  info: (msg: string, opts?: Omit<NotifyOptions, 'status'>) =>
    core(msg, { ...opts, status: 'primary' }),
  warn: (msg: string, opts?: Omit<NotifyOptions, 'status'>) =>
    core(msg, { ...opts, status: 'warning' }),
  error: (msg: string, opts?: Omit<NotifyOptions, 'status'>) =>
    core(msg, { ...opts, status: 'danger', timeout: opts?.timeout ?? 5000 }),
};

// Helper to wrap a promise and show error notification automatically.
export async function withErrorNotify<T>(
  p: Promise<T>,
  errorMessage = 'エラーが発生しました',
): Promise<T | undefined> {
  try {
    return await p;
  } catch (e) {
    notify.error(errorMessage);
    return undefined;
  }
}
