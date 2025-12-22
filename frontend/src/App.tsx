import { useState, useCallback } from 'react';
import { verifyUser, sendCode, verifyCode, resetPassword } from './api';
import type { ApiError } from './api';
import { AxiosError } from 'axios';
import './index.css';

// 步骤枚举
type Step = 'username' | 'code' | 'password' | 'success';

// 图标组件
const LockIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

function App() {
  // 状态管理
  const [step, setStep] = useState<Step>('username');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // 错误处理
  const handleError = useCallback((err: unknown) => {
    if (err instanceof AxiosError && err.response?.data) {
      const apiError = err.response.data as ApiError;
      setError(apiError.error || '发生未知错误');
    } else {
      setError('网络错误，请检查连接');
    }
  }, []);

  // 步骤1: 验证用户名
  const handleVerifyUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('请输入用户名');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await verifyUser(username);
      setEmail(result.email);

      // 发送验证码
      await sendCode(username, result.email);
      setStep('code');
      startCountdown();
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  // 开始倒计时
  const startCountdown = () => {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // 重发验证码
  const handleResendCode = async () => {
    if (countdown > 0) return;

    setLoading(true);
    setError('');

    try {
      await sendCode(username, email);
      startCountdown();
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  // 步骤2: 验证验证码
  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6) {
      setError('请输入6位验证码');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await verifyCode(username, code);
      setToken(result.token);
      setStep('password');
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  // 步骤3: 重置密码
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password.length < 8) {
      setError('密码长度至少8位');
      return;
    }

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await resetPassword(username, password, token);
      setStep('success');
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  // 密码强度计算
  const getPasswordStrength = (pwd: string): number => {
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (/[A-Z]/.test(pwd)) strength++;
    if (/[a-z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[^A-Za-z0-9]/.test(pwd)) strength++;
    return Math.min(strength, 4);
  };

  const passwordStrength = getPasswordStrength(password);

  // 遮蔽邮箱
  const maskEmail = (email: string): string => {
    if (!email) return '';
    const [local, domain] = email.split('@');
    if (local.length <= 2) return email;
    return `${local[0]}${'*'.repeat(local.length - 2)}${local[local.length - 1]}@${domain}`;
  };

  // 重新开始
  const handleReset = () => {
    setStep('username');
    setUsername('');
    setEmail('');
    setCode('');
    setPassword('');
    setConfirmPassword('');
    setToken('');
    setError('');
  };

  return (
    <div className="page-wrapper">
      <div className="container">
        {/* Logo */}
        <div className="logo">
          <LockIcon />
        </div>

        {/* 步骤指示器 */}
        {step !== 'success' && (
          <div className="steps">
            <div className={`step ${step === 'username' ? 'active' : 'completed'}`}>1</div>
            <div className={`step-line ${step !== 'username' ? 'completed' : ''}`} />
            <div className={`step ${step === 'code' ? 'active' : step === 'password' ? 'completed' : ''}`}>2</div>
            <div className={`step-line ${step === 'password' ? 'completed' : ''}`} />
            <div className={`step ${step === 'password' ? 'active' : ''}`}>3</div>
          </div>
        )}

        <div className="card">
          {/* 错误提示 */}
          {error && (
            <div className="alert alert-error">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {/* 步骤1: 用户名输入 */}
          {step === 'username' && (
            <>
              <h1 className="page-title">密码重置</h1>
              <p className="page-subtitle">请输入您的用户名，我们将发送验证码到您的邮箱</p>

              <form onSubmit={handleVerifyUser}>
                <div className="form-group">
                  <input
                    type="text"
                    className="form-input"
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoFocus
                    disabled={loading}
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" /> : null}
                  {loading ? '验证中...' : '下一步'}
                </button>
              </form>
            </>
          )}

          {/* 步骤2: 验证码输入 */}
          {step === 'code' && (
            <>
              <h1 className="page-title">输入验证码</h1>
              <p className="page-subtitle">
                验证码已发送至 <strong>{maskEmail(email)}</strong>
              </p>

              <form onSubmit={handleVerifyCode}>
                <div className="form-group">
                  <input
                    type="text"
                    className="form-input"
                    placeholder="请输入6位验证码"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    autoFocus
                    disabled={loading}
                    style={{ textAlign: 'center', letterSpacing: '0.5em', fontSize: '1.25rem' }}
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={loading || code.length !== 6}>
                  {loading ? <span className="spinner" /> : null}
                  {loading ? '验证中...' : '验证'}
                </button>

                <div className="countdown">
                  {countdown > 0 ? (
                    <span>{countdown}秒后可重新发送</span>
                  ) : (
                    <span className="countdown-resend" onClick={handleResendCode}>
                      重新发送验证码
                    </span>
                  )}
                </div>
              </form>
            </>
          )}

          {/* 步骤3: 设置新密码 */}
          {step === 'password' && (
            <>
              <h1 className="page-title">设置新密码</h1>

              <form onSubmit={handleResetPassword}>
                <div className="form-group">
                  <label className="form-label">新密码</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="至少8位，包含字母和数字"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoFocus
                    disabled={loading}
                  />
                  {password && (
                    <div className="password-strength">
                      {[1, 2, 3, 4].map((level) => (
                        <div
                          key={level}
                          className={`password-strength-bar ${passwordStrength >= level
                            ? passwordStrength <= 2
                              ? 'weak'
                              : passwordStrength === 3
                                ? 'medium'
                                : 'strong'
                            : ''
                            }`}
                        />
                      ))}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">确认密码</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="再次输入新密码"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    disabled={loading}
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? <span className="spinner" /> : null}
                  {loading ? '重置中...' : '重置密码'}
                </button>
              </form>
            </>
          )}

          {/* 步骤4: 成功页面 */}
          {step === 'success' && (
            <>
              <div className="success-icon">
                <CheckIcon />
              </div>
              <h1 className="page-title">密码重置成功！</h1>
              <p className="page-subtitle">您的密码已成功更新，请使用新密码登录</p>

              <button className="btn btn-primary" onClick={handleReset}>
                返回首页
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
