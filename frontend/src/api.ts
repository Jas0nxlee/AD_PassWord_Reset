function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

interface ApiError {
  error?: string;
}

async function ensureCsrfToken(): Promise<string> {
  let token = getCsrfToken();
  if (!token) {
    await fetch('/api/csrf', { credentials: 'same-origin', cache: 'no-store' });
    token = getCsrfToken();
  }
  if (!token) throw new ApiRequestError('无法建立安全会话，请刷新页面后重试');
  return token;
}

async function post<T>(path: string, body: Record<string, string>): Promise<T> {
  const csrfToken = await ensureCsrfToken();
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify(body),
  });

  const payload = await response.json().catch(() => ({})) as T & ApiError;
  if (!response.ok) throw new ApiRequestError(payload.error || '请求失败，请稍后重试');
  return payload;
}

export interface SendCodeResponse {
  message: string;
}

export interface VerifyCodeResponse {
  message: string;
  token: string;
}

export interface ResetPasswordResponse {
  message: string;
}

export function sendCode(username: string): Promise<SendCodeResponse> {
  return post('/send-code', { username });
}

export function verifyCode(username: string, code: string): Promise<VerifyCodeResponse> {
  return post('/verify-code', { username, code });
}

export function resetPassword(
  username: string,
  newPassword: string,
  token: string,
): Promise<ResetPasswordResponse> {
  return post('/reset-password', { username, new_password: newPassword, token });
}
