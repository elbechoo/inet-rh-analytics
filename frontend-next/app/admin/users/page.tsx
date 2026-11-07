'use client';
import { useEffect, useState } from 'react';
import { Users, ShieldCheck, UserX, ChevronLeft, ChevronRight, KeyRound, Eye, EyeOff, X } from 'lucide-react';
import { authFetch } from '@/app/lib/api';

const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  admin:   { bg: 'rgba(248,81,73,0.15)',   color: '#f85149' },
  rh:      { bg: 'rgba(227,179,65,0.15)',  color: '#e3b341' },
  employe: { bg: 'rgba(46,160,67,0.15)',   color: '#3fb950' },
};

export default function AdminUsers() {
  const [users,      setUsers]     = useState<any[]>([]);
  const [search,     setSearch]    = useState('');
  const [filterRole, setFilter]    = useState('all');
  const [loading,    setLoading]   = useState(true);
  const [toast,      setToast]     = useState<{ text: string; ok: boolean } | null>(null);
  const [page,       setPage]      = useState(1);
  const [pwdModal,   setPwdModal]  = useState<{ uid: number; name: string } | null>(null);
  const [newPwd,     setNewPwd]    = useState('');
  const [showPwd,    setShowPwd]   = useState(false);
  const [resetting,  setResetting] = useState(false);
  const PAGE_SIZE = 10;

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const load = () => {
    authFetch('/api/admin/users').then(r => r.json()).then(d => { setUsers(d); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  const changeRole = async (uid: number, role: string) => {
    await authFetch(`/api/admin/users/${uid}/role`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    showToast('Role updated successfully');
    load();
  };

  const toggleStatut = async (uid: number, current: string) => {
    const next = current === 'Actif' ? 'Inactif' : 'Actif';
    await authFetch(`/api/admin/users/${uid}/statut`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ statut: next }),
    });
    showToast(`Status changed to ${next === 'Actif' ? 'Active' : 'Inactive'}`);
    load();
  };

  const openPwdModal = (uid: number, name: string) => {
    setNewPwd('');
    setShowPwd(false);
    setPwdModal({ uid, name });
  };

  const confirmResetPwd = async () => {
    if (!pwdModal || !newPwd.trim()) return;
    setResetting(true);
    const res = await authFetch(`/api/admin/users/${pwdModal.uid}/reset-password`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPwd }),
    });
    setResetting(false);
    setPwdModal(null);
    if (res.ok) showToast('Password reset successfully');
    else showToast('Failed to reset password', false);
  };

  const filtered   = users.filter(u => {
    const matchSearch = `${u.nom} ${u.prenom} ${u.username}`.toLowerCase().includes(search.toLowerCase());
    const matchRole   = filterRole === 'all' || u.role === filterRole;
    return matchSearch && matchRole;
  });
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 999,
          background: toast.ok ? 'rgba(46,160,67,0.2)' : 'rgba(248,81,73,0.2)',
          color: toast.ok ? '#3fb950' : '#f85149',
          border: `1px solid ${toast.ok ? 'rgba(46,160,67,0.4)' : 'rgba(248,81,73,0.4)'}`,
          padding: '12px 20px', borderRadius: 10, fontSize: '0.84rem', fontWeight: 600,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        }}>
          {toast.text}
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>User Management</h1>
          <p style={{ color: '#6B879B', marginTop: 4, fontSize: '0.82rem' }}>{users.length} users total</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {[
            { label: 'Total',    value: users.length,                                   color: '#45B9E9', bg: 'rgba(15,163,224,0.15)',  Icon: Users },
            { label: 'Active',   value: users.filter(u => u.statut === 'Actif').length, color: '#3fb950', bg: 'rgba(46,160,67,0.15)',   Icon: ShieldCheck },
            { label: 'Inactive', value: users.filter(u => u.statut !== 'Actif').length, color: '#f85149', bg: 'rgba(248,81,73,0.15)',  Icon: UserX },
          ].map((k, i) => (
            <div key={i} style={{ background: k.bg, borderRadius: 10, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <k.Icon size={15} style={{ color: k.color }} />
              <span style={{ fontWeight: 700, color: k.color, fontSize: '0.95rem' }}>{k.value}</span>
              <span style={{ fontSize: '0.70rem', color: k.color, fontWeight: 600, opacity: 0.7 }}>{k.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <input
          placeholder="Search by name or username..."
          value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          style={{ flex: 1, padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border)', fontSize: '0.84rem', outline: 'none', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }}
          onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
          onBlur={e => (e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)')}
        />
        {['all', 'admin', 'rh', 'employe'].map(r => (
          <button key={r} onClick={() => { setFilter(r); setPage(1); }} style={{
            padding: '10px 18px', borderRadius: 10, border: '1.5px solid',
            borderColor: filterRole === r ? '#0FA3E0' : 'rgba(12,36,54,0.04)',
            background: filterRole === r ? 'rgba(15,163,224,0.15)' : 'rgba(12,36,54,0.04)',
            color: filterRole === r ? '#45B9E9' : '#6B879B',
            fontWeight: filterRole === r ? 700 : 500, fontSize: '0.82rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif',
          }}>
            {r === 'all' ? 'All' : r === 'rh' ? 'HR' : r.charAt(0).toUpperCase() + r.slice(1)}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'rgba(12,36,54,0.04)', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>
              {['Employee', 'Username', 'Role', 'Status', 'Email', 'Actions'].map(h => (
                <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.64rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: '#9DB3C2', fontSize: '0.84rem' }}>Loading...</td></tr>
            ) : paginated.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: '#9DB3C2', fontSize: '0.84rem' }}>No results found</td></tr>
            ) : paginated.map((u) => {
              const rc = ROLE_COLORS[u.role] ?? ROLE_COLORS.employe;
              return (
                <tr key={u.user_id} style={{ borderTop: '1px solid rgba(12,36,54,0.04)', transition: 'background 0.1s' }}
                  onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                  onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '13px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--brand-600)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, color: 'white', flexShrink: 0 }}>
                        {u.prenom?.[0]}{u.nom?.[0]}
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, color: '#0C2436', fontSize: '0.85rem' }}>{u.prenom} {u.nom}</div>
                        <div style={{ color: '#9DB3C2', fontSize: '0.70rem' }}>ID {u.user_id}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '13px 16px', fontSize: '0.80rem', color: '#34546A', fontFamily: 'monospace' }}>{u.username}</td>
                  <td style={{ padding: '13px 16px' }}>
                    <select value={u.role} onChange={e => changeRole(u.user_id, e.target.value)}
                      style={{ padding: '4px 10px', borderRadius: 8, border: `1.5px solid ${rc.color}44`, background: rc.bg, color: rc.color, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', outline: 'none' }}>
                      <option value="employe">Employee</option>
                      <option value="rh">HR</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td style={{ padding: '13px 16px' }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700,
                      background: u.statut === 'Actif' ? 'rgba(46,160,67,0.2)'  : 'rgba(248,81,73,0.2)',
                      color:      u.statut === 'Actif' ? '#3fb950'              : '#f85149',
                    }}>
                      {u.statut === 'Actif' ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={{ padding: '13px 16px', fontSize: '0.78rem', color: '#6B879B' }}>{u.email}</td>
                  <td style={{ padding: '13px 16px' }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={() => toggleStatut(u.user_id, u.statut)} style={{
                        padding: '5px 12px', borderRadius: 7, border: '1px solid var(--border)',
                        background: 'rgba(12,36,54,0.04)', color: '#34546A', fontSize: '0.75rem', cursor: 'pointer', fontFamily: 'Inter, sans-serif',
                      }}>
                        {u.statut === 'Actif' ? 'Disable' : 'Enable'}
                      </button>
                      <button onClick={() => openPwdModal(u.user_id, `${u.prenom} ${u.nom}`)} style={{
                        padding: '5px 10px', borderRadius: 7, border: '1.5px solid rgba(15,163,224,0.3)',
                        background: 'rgba(15,163,224,0.15)', color: '#45B9E9', fontSize: '0.75rem', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 4,
                      }}>
                        <KeyRound size={11} /> Reset
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
            <span style={{ fontSize: '0.78rem', color: '#6B879B' }}>
              {filtered.length} users - page {page} / {totalPages}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{
                padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)',
                background: page === 1 ? 'rgba(12,36,54,0.04)' : 'rgba(12,36,54,0.04)', color: page === 1 ? '#9DB3C2' : '#34546A',
                cursor: page === 1 ? 'not-allowed' : 'pointer', fontSize: '0.80rem', display: 'flex', alignItems: 'center',
              }}>
                <ChevronLeft size={14} />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
                <button key={n} onClick={() => setPage(n)} style={{
                  padding: '6px 12px', borderRadius: 8, border: '1.5px solid',
                  borderColor: page === n ? '#0FA3E0' : 'rgba(12,36,54,0.04)',
                  background: page === n ? 'rgba(15,163,224,0.15)' : 'rgba(12,36,54,0.04)',
                  color: page === n ? '#45B9E9' : '#34546A',
                  fontWeight: page === n ? 700 : 400, fontSize: '0.80rem', cursor: 'pointer',
                }}>{n}</button>
              ))}
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{
                padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border)',
                background: page === totalPages ? 'rgba(12,36,54,0.04)' : 'rgba(12,36,54,0.04)', color: page === totalPages ? '#9DB3C2' : '#34546A',
                cursor: page === totalPages ? 'not-allowed' : 'pointer', fontSize: '0.80rem', display: 'flex', alignItems: 'center',
              }}>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Password Reset Modal */}
      {pwdModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setPwdModal(null)}>
          <div style={{
            background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid rgba(255,255,255,0.12)',
            padding: '28px 32px', width: 380, boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div>
                <h3 style={{ margin: 0, color: '#0C2436', fontSize: '1rem', fontWeight: 700 }}>Reset Password</h3>
                <p style={{ margin: '4px 0 0', color: '#6B879B', fontSize: '0.78rem' }}>{pwdModal.name}</p>
              </div>
              <button onClick={() => setPwdModal(null)} style={{ background: 'none', border: 'none', color: '#9DB3C2', cursor: 'pointer', padding: 4 }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ position: 'relative', marginBottom: 20 }}>
              <input
                type={showPwd ? 'text' : 'password'}
                placeholder="New password"
                value={newPwd}
                onChange={e => setNewPwd(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && confirmResetPwd()}
                autoFocus
                style={{
                  width: '100%', padding: '10px 40px 10px 14px', borderRadius: 8,
                  border: '1.5px solid rgba(255,255,255,0.1)', background: 'rgba(12,36,54,0.04)',
                  color: '#0C2436', fontSize: '0.85rem', outline: 'none', fontFamily: 'Inter, sans-serif',
                  boxSizing: 'border-box',
                }}
                onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
                onBlur={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
              />
              <button onClick={() => setShowPwd(v => !v)} style={{
                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: '#9DB3C2', cursor: 'pointer', padding: 2,
              }}>
                {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setPwdModal(null)} style={{
                padding: '8px 18px', borderRadius: 8, border: '1px solid var(--border)',
                background: 'rgba(12,36,54,0.04)', color: '#6B879B', fontSize: '0.82rem', cursor: 'pointer', fontFamily: 'Inter, sans-serif',
              }}>
                Cancel
              </button>
              <button onClick={confirmResetPwd} disabled={!newPwd.trim() || resetting} style={{
                padding: '8px 18px', borderRadius: 8, border: '1.5px solid rgba(15,163,224,0.4)',
                background: newPwd.trim() ? 'rgba(15,163,224,0.2)' : 'rgba(15,163,224,0.06)',
                color: newPwd.trim() ? '#45B9E9' : '#4f4f8a',
                fontSize: '0.82rem', cursor: newPwd.trim() ? 'pointer' : 'not-allowed',
                fontWeight: 600, fontFamily: 'Inter, sans-serif',
              }}>
                {resetting ? 'Resetting...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
