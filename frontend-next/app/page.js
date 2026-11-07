'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Mail, Lock, Eye, EyeOff, AlertCircle, Loader2, ArrowRight, BarChart3, Brain, ShieldCheck, Users } from 'lucide-react';
import { LogoWordmark, LogoMark } from './components/Logo';

export default function LoginPage() {
  const [form, setForm]         = useState({ username: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');
  const router = useRouter();

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: form.username, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 429) { setError('Too many attempts. Please wait a few minutes and try again.'); return; }
        setError(data.detail || 'Invalid credentials'); return;
      }
      const { access_token, token_type, ...userInfo } = data;
      localStorage.setItem('inet_user', JSON.stringify(userInfo));
      if (data.role === 'admin')   router.push('/admin/dashboard');
      else if (data.role === 'rh') router.push('/hr/dashboard');
      else                         router.push('/employe/dashboard');
    } catch {
      setError('Unable to reach the server. Please try again.');
    } finally { setLoading(false); }
  }

  const features = [
    { icon: Users,       t: 'Workforce management', d: 'Employees, contracts and departments in one place' },
    { icon: BarChart3,   t: 'Live analytics',        d: 'Attendance, absence and lateness in real time' },
    { icon: Brain,       t: 'Predictive insight',    d: 'Absenteeism risk with the reasons behind it' },
    { icon: ShieldCheck, t: 'Role-based access',     d: 'Separate spaces for HR, admin and employees' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>

      {/* left - brand plate, the logo's navy */}
      <div className="hidden lg:flex" style={{
        width: '46%', minWidth: 440, background: 'var(--card)', borderRight: '1px solid var(--border)',
        flexDirection: 'column', justifyContent: 'space-between',
        padding: '48px 52px', position: 'relative', overflow: 'hidden',
      }}>
        <div aria-hidden style={{
          position: 'absolute', top: -140, right: -120, width: 460, height: 460,
          borderRadius: '50%', background: 'rgba(15,163,224,.13)', filter: 'blur(90px)',
        }} />
        <div aria-hidden style={{
          position: 'absolute', bottom: -120, left: -90, width: 340, height: 340,
          borderRadius: '50%', background: 'rgba(15,163,224,.08)', filter: 'blur(80px)',
        }} />

        <div style={{ position: 'relative', zIndex: 1 }} className="animate-fadein">
          <LogoWordmark size={46} subtitle="Système de Gestion RH Intelligente" />
        </div>

        <div style={{ position: 'relative', zIndex: 1 }}>
          <h1 className="animate-fadeup" style={{
            fontSize: '2.15rem', lineHeight: 1.16, letterSpacing: '-.035em',
            fontWeight: 700, color: 'var(--ink)', marginBottom: 12, maxWidth: 400,
          }}>
            Smart HR management,<br />backed by your data.
          </h1>
          <p className="animate-fadeup" style={{
            animationDelay: '80ms', fontSize: '.9rem', lineHeight: 1.65,
            color: 'var(--ink-2)', maxWidth: 380, marginBottom: 34,
          }}>
            Track attendance, manage leave and anticipate absenteeism from a single
            platform - with dashboards your management team will actually read.
          </p>

          <div className="stagger" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {features.map(({ icon: Icon, t, d }) => (
              <div key={t} style={{
                background: 'var(--sky-50)', border: '1px solid var(--sky-100)',
                borderRadius: 12, padding: '15px 16px',
              }}>
                <Icon size={16} style={{ color: '#45B9E9', marginBottom: 9 }} />
                <div style={{ fontSize: '.79rem', fontWeight: 620, color: 'var(--ink)', marginBottom: 3 }}>{t}</div>
                <div style={{ fontSize: '.72rem', lineHeight: 1.45, color: 'var(--muted)' }}>{d}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ position: 'relative', zIndex: 1, fontSize: '.72rem', color: 'var(--faint)' }}>
          © {new Date().getFullYear()} iNET RH
        </div>
      </div>

      {/* right - form */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 32px', background: 'var(--bg)',
      }}>
        <div style={{ width: '100%', maxWidth: 384 }} className="animate-fadeup">
          <div className="lg:hidden" style={{ marginBottom: 26 }}>
            <LogoWordmark size={42} subtitle={null} />
          </div>

          <h2 style={{ fontSize: '1.45rem', fontWeight: 700, letterSpacing: '-.03em', color: 'var(--ink)' }}>
            Sign in
          </h2>
          <p className="t-meta" style={{ marginTop: 4, marginBottom: 26 }}>
            Enter your credentials to access your workspace.
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
            <Field label="Username or email" icon={Mail} type="text"
                   placeholder="firstname.lastname" value={form.username}
                   onChange={v => setForm({ ...form, username: v })} autoComplete="username" />
            <Field label="Password" icon={Lock} type={showPass ? 'text' : 'password'}
                   placeholder="••••••••" value={form.password}
                   onChange={v => setForm({ ...form, password: v })} autoComplete="current-password"
                   trailing={
                     <button type="button" onClick={() => setShowPass(!showPass)}
                             aria-label={showPass ? 'Hide password' : 'Show password'}
                             style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                                      background: 'none', border: 'none', cursor: 'pointer',
                                      color: 'var(--faint)', display: 'flex', padding: 6, borderRadius: 6 }}>
                       {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                     </button>
                   } />

            {error && (
              <div role="alert" className="animate-fadein" style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                background: '#FDECEC', border: '1px solid #F8D5D5', color: '#B01C1C',
                fontSize: '.8rem', padding: '10px 12px', borderRadius: 9, lineHeight: 1.5,
              }}>
                <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} /> {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary" style={{ width: '100%', padding: 12, marginTop: 3 }}>
              {loading
                ? <><Loader2 size={15} style={{ animation: 'spin .8s linear infinite' }} /> Signing in...</>
                : <>Sign in <ArrowRight size={15} /></>}
            </button>
          </form>

          <p className="t-meta" style={{ marginTop: 20, fontSize: '.74rem' }}>
            Trouble signing in? Contact your HR administrator.
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, icon: Icon, trailing, onChange, ...rest }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: 'var(--ink-2)', marginBottom: 6 }}>
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        <span style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)',
                       color: 'var(--faint)', display: 'flex', pointerEvents: 'none' }}>
          <Icon size={15} />
        </span>
        <input {...rest} required onChange={e => onChange(e.target.value)}
               style={{ paddingLeft: 35, paddingRight: trailing ? 40 : 12, paddingTop: 11, paddingBottom: 11 }} />
        {trailing}
      </div>
    </div>
  );
}
