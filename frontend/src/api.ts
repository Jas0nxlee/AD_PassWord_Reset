import axios from 'axios';

// 从 Cookie 读取 CSRF Token
function getCsrfToken(): string | null {
    const match = document.cookie.match(/csrf_token=([^;]+)/);
    return match ? match[1] : null;
}

// 创建 axios 实例
const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器：自动添加 CSRF Token
api.interceptors.request.use((config) => {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
    }
    return config;
});

// API 接口
export interface VerifyUserResponse {
    message: string;
    masked_email: string;
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

export interface ApiError {
    error: string;
}

// 验证用户
export async function verifyUser(username: string): Promise<VerifyUserResponse> {
    const response = await api.post<VerifyUserResponse>('/verify-user', { username });
    return response.data;
}

// 发送验证码
export async function sendCode(username: string): Promise<SendCodeResponse> {
    const response = await api.post<SendCodeResponse>('/send-code', { username });
    return response.data;
}

// 验证验证码
export async function verifyCode(username: string, code: string): Promise<VerifyCodeResponse> {
    const response = await api.post<VerifyCodeResponse>('/verify-code', { username, code });
    return response.data;
}

// 重置密码
export async function resetPassword(
    username: string,
    newPassword: string,
    token: string
): Promise<ResetPasswordResponse> {
    const response = await api.post<ResetPasswordResponse>('/reset-password', {
        username,
        new_password: newPassword,
        token,
    });
    return response.data;
}

export default api;
