// The JWT lives in an httpOnly cookie set by the backend on login, so the
// browser sends it automatically on same-origin /api/* requests and no token is
// readable from JavaScript. `authFetch` stays the single call site for fetches.
export function authFetch(url: string, opts: RequestInit = {}): Promise<Response> {
  return fetch(url, {
    ...opts,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    },
  });
}

// Clears the session server-side (deletes the httpOnly cookie) and locally.
export async function logout(): Promise<void> {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  } catch {
    /* ignore network errors on logout */
  }
  if (typeof window !== 'undefined') {
    localStorage.removeItem('inet_user');
  }
}
