import { useCallback, useEffect, useState } from 'react';
import { ApiRequestError, resetPassword, sendCode, verifyCode } from './api';
import './index.css';

type Step = 'username' | 'code' | 'password' | 'success';

const LockIcon = () => (
  <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const CheckIcon = () => (
  <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

function passwordCategories(password: string): number {
  return [/[A-Z]/, /[a-z]/, /[0-9]/, /[^A-Za-z0-9]/]
    .filter((pattern) => pattern.test(password)).length;
}

function App() {
  const [step, setStep] = useState<Step>('username');
  const [username, setUsername] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  const handleError = useCallback((err: unknown) => {
    if (err instanceof ApiRequestError) {
      setError(err.message || '请求失败，请稍后重试');
    } else {
      setError('网络错误，请检查连接');
    }
  }, []);

  const handleRequestCode = async (event: React.FormEvent) => {
    event.preventDefault();
    const normalizedUsername = username.trim();
    if (!normalizedUsername) {
      setError('请输入用户名');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await sendCode(normalizedUsername);
      setUsername(normalizedUsername);
      setStep('code');
      setCountdown(60);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (countdown > 0 || loading) return;
    setLoading(true);
    setError('');
    try {
      await sendCode(username);
      setCountdown(60);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError('请输入6位数字验证码');
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

  const handleResetPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password.length < 12 || passwordCategories(password) < 3) {
      setError('密码至少12位，并包含大写字母、小写字母、数字、特殊字符中的至少三类');
      return;
    }
    if (password.toLocaleLowerCase().includes(username.toLocaleLowerCase())) {
      setError('密码不能包含用户名');
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
      setPassword('');
      setConfirmPassword('');
      setToken('');
      setStep('success');
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  const passwordStrength = Math.min(
    (password.length >= 12 ? 1 : 0) + passwordCategories(password),
    4,
  );

  const handleReset = () => {
    setStep('username');
    setUsername('');
    setCode('');
    setPassword('');
    setConfirmPassword('');
    setToken('');
    setError('');
    setCountdown(0);
  };

  return (
    <div className="page-wrapper">
      <main className="container">
        <div className="logo"><LockIcon /></div>

        {step !== 'success' && (
          <div className="steps" aria-label="密码重置进度">
            <div className={`step ${step === 'username' ? 'active' : 'completed'}`}>1</div>
            <div className={`step-line ${step !== 'username' ? 'completed' : ''}`} />
            <div className={`step ${step === 'code' ? 'active' : step === 'password' ? 'completed' : ''}`}>2</div>
            <div className={`step-line ${step === 'password' ? 'completed' : ''}`} />
            <div className={`step ${step === 'password' ? 'active' : ''}`}>3</div>
          </div>
        )}

        <div className="card">
          {error && (
            <div className="alert alert-error" role="alert" aria-live="assertive">
              <span aria-hidden="true">⚠️</span><span>{error}</span>
            </div>
          )}

          {step === 'username' && (
            <>
              <h1 className="page-title">密码重置</h1>
              <p className="page-subtitle">请输入用户名；如账号符合条件，我们将发送验证码</p>
              <form onSubmit={handleRequestCode}>
                <div className="form-group">
                  <label className="form-label" htmlFor="username">用户名</label>
                  <input id="username" type="text" className="form-input" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" spellCheck={false} autoFocus disabled={loading} />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading && <span className="spinner" />}{loading ? '发送中...' : '发送验证码'}
                </button>
              </form>
            </>
          )}

          {step === 'code' && (
            <>
              <h1 className="page-title">输入验证码</h1>
              <p className="page-subtitle">如账号符合条件，验证码将发送到预留邮箱</p>
              <form onSubmit={handleVerifyCode}>
                <div className="form-group">
                  <label className="form-label" htmlFor="verification-code">6位验证码</label>
                  <input id="verification-code" type="text" className="form-input verification-code-input" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" maxLength={6} autoFocus disabled={loading} />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading || code.length !== 6}>
                  {loading && <span className="spinner" />}{loading ? '验证中...' : '验证'}
                </button>
                <div className="countdown">
                  {countdown > 0 ? <span>{countdown}秒后可重新发送</span> : (
                    <button type="button" className="countdown-resend" onClick={handleResendCode} disabled={loading}>重新发送验证码</button>
                  )}
                </div>
              </form>
            </>
          )}

          {step === 'password' && (
            <>
              <h1 className="page-title">设置新密码</h1>
              <p className="page-subtitle">至少12位，并包含四类字符中的至少三类</p>
              <form onSubmit={handleResetPassword}>
                <div className="form-group">
                  <label className="form-label" htmlFor="new-password">新密码</label>
                  <input id="new-password" type="password" className="form-input" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" autoFocus disabled={loading} />
                  {password && <div className="password-strength" aria-label={`密码强度 ${passwordStrength}/4`}>
                    {[1, 2, 3, 4].map((level) => <div key={level} className={`password-strength-bar ${passwordStrength >= level ? passwordStrength <= 2 ? 'weak' : passwordStrength === 3 ? 'medium' : 'strong' : ''}`} />)}
                  </div>}
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="confirm-password">确认密码</label>
                  <input id="confirm-password" type="password" className="form-input" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" disabled={loading} />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading && <span className="spinner" />}{loading ? '重置中...' : '重置密码'}
                </button>
              </form>
            </>
          )}

          {step === 'success' && (
            <div role="status">
              <div className="success-icon"><CheckIcon /></div>
              <h1 className="page-title">密码重置成功</h1>
              <p className="page-subtitle">请使用新密码登录；确认邮件将发送到预留邮箱</p>
              <button type="button" className="btn btn-primary" onClick={handleReset}>返回首页</button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
