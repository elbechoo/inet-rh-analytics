'use client';
import { useState, useEffect, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Home, Bell, Search, ChevronRight, LogOut, Settings, X, CheckCircle2, Menu } from 'lucide-react';
import { logout as doLogout } from '../lib/api';

const PAGE_LABELS: Record<string, string> = {
  '/hr/dashboard':        'Dashboard',
  '/hr/employes':         'Employees',
  '/hr/pointage':         'Attendance',
  '/hr/absences':         'Absences',
  '/hr/demandes':         'Leave Requests',
  '/hr/validations':      'Validations',
  '/hr/stats':            'Statistics',
  '/hr/alertes':          'AI Alerts',
  '/hr/formations':       'Training',
  '/hr/formations-perso': 'My Training',
  '/admin/dashboard':     'Dashboard',
  '/admin/users':         'Users',
  '/admin/depts':         'Departments',
  '/admin/config':        'Configuration',
  '/admin/logs':          'System Logs',
  '/employe/dashboard':   'Dashboard',
  '/employe/pointage':    'Attendance',
  '/employe/demandes':    'My Requests',
  '/employe/formations':  'Training',
  '/employe/profil':      'My Profile',
};

const NIV_CFG: Record<string, { color: string; bg: string }> = {
  Critique: { color: '#f85149', bg: 'rgba(248,81,73,0.15)' },
  Moyen:    { color: '#e3b341', bg: 'rgba(227,179,65,0.15)' },
  Info:     { color: '#45B9E9', bg: 'rgba(15,163,224,0.15)' },
};

export default function TopBar({ onMenu }: { onMenu?: () => void } = {}) {
  const pathname = usePathname();
  const router   = useRouter();
  const [time,    setTime]    = useState('');
  const [dateStr, setDateStr] = useState('');
  const [user,    setUser]    = useState<any>(null);

  const [searchQuery,   setSearchQuery]   = useState('');
  const [searchOpen,    setSearchOpen]    = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [allEmployes,   setAllEmployes]   = useState<any[]>([]);
  const searchRef = useRef<HTMLDivElement>(null);

  const [bellOpen,  setBellOpen]  = useState(false);
  const [alertes,   setAlertes]   = useState<any[]>([]);
  const [unreadCnt, setUnreadCnt] = useState(0);
  const bellRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const u = localStorage.getItem('inet_user');
    if (u) try { setUser(JSON.parse(u)); } catch {}
    function tick() {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
      setDateStr(now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }));
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch('/api/employes/').then(r => r.json()).then(d => {
      if (Array.isArray(d)) setAllEmployes(d);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    // Scope the bell by role:
    //   * an employee must see ONLY their own alerts (privacy — Riadh's
    //     absenteeism-risk score is confidential HR data and must not leak
    //     to a colleague viewing their own dashboard);
    //   * an HR manager / administrator keeps the global feed.
    // We wait for `user` to hydrate from localStorage before firing the
    // request, otherwise an employee would briefly see the global feed
    // during the first render.
    if (!user) return;
    const role = user?.role;
    const empId = user?.employe?.employe_id;
    const url = (role === 'employe' && empId)
      ? `/api/ai/alertes?limit=8&employe_id=${empId}`
      : `/api/ai/alertes?limit=8`;
    fetch(url).then(r => r.json()).then(d => {
      if (Array.isArray(d)) {
        setAlertes(d);
        setUnreadCnt(d.filter((a: any) => !a.est_lue).length);
      }
    }).catch(() => {});
  }, [user]);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false); setSearchQuery(''); setSearchResults([]);
      }
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults([]); return; }
    const q = searchQuery.toLowerCase();
    setSearchResults(
      allEmployes.filter((e: any) =>
        `${e.prenom} ${e.nom}`.toLowerCase().includes(q) ||
        (e.matricule || '').toLowerCase().includes(q) ||
        (e.poste || '').toLowerCase().includes(q)
      ).slice(0, 6)
    );
  }, [searchQuery, allEmployes]);

  const emp       = user?.employe || {};
  const role      = user?.role;
  const initials  = emp.prenom && emp.nom ? `${emp.prenom[0]}${emp.nom[0]}`.toUpperCase() : role === 'admin' ? 'AD' : role === 'rh' ? 'RH' : 'EMP';
  const roleLabel = role === 'admin' ? 'Administrator' : role === 'rh' ? 'HR Manager' : 'Employee';
  const avatarBg  = role === 'admin' ? 'linear-gradient(135deg,#17557A,#0F3E5A)' : 'var(--brand-600)';
  const section   = pathname.startsWith('/admin') ? 'Administrator' : pathname.startsWith('/hr') ? 'HR Manager' : 'Employee';
  const pageLabel = PAGE_LABELS[pathname] ?? '';
  const settingsPath = role === 'admin' ? '/admin/config' : role === 'rh' ? '/hr/stats' : '/employe/profil';
  const alertsPath   = role === 'employe' ? '/employe/dashboard' : '/hr/alertes';

  async function logout() { await doLogout(); router.push('/'); }

  return (
    <header style={{
      height: 56, background: 'var(--card)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16,
      flexShrink: 0, position: 'sticky', top: 0, zIndex: 40,
    }}>

      {/* Drawer toggle — hidden above 900px by the .mobile-navbtn rule. */}
      {onMenu && (
        <button className="mobile-navbtn" onClick={onMenu} aria-label="Open menu">
          <Menu size={17} />
        </button>
      )}

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: '#6B879B', flexShrink: 0 }}>
        <Home size={14} />
        <ChevronRight size={12} />
        <span style={{ color: '#34546A', fontWeight: 500 }}>{section}</span>
        {pageLabel && <>
          <ChevronRight size={12} />
          <span style={{ color: '#0C2436', fontWeight: 600 }}>{pageLabel}</span>
        </>}
      </div>

      {/* Search */}
      <div ref={searchRef} style={{ flex: 1, maxWidth: 380, marginLeft: 8, position: 'relative' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: searchOpen ? 'rgba(12,36,54,0.04)' : 'rgba(12,36,54,0.04)',
          border: searchOpen ? '1px solid rgba(15,163,224,0.5)' : '1px solid rgba(12,36,54,0.04)',
          borderRadius: 8, padding: '6px 12px', transition: 'all 0.15s',
        }}>
          <Search size={14} color={searchOpen ? '#45B9E9' : '#9DB3C2'} style={{ flexShrink: 0 }} />
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search employees..."
            style={{ background: 'none', border: 'none', outline: 'none', fontSize: '0.78rem', color: '#0C2436', flex: 1, width: '100%' }}
          />
          {searchQuery && (
            <button onClick={() => { setSearchQuery(''); setSearchResults([]); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9DB3C2', padding: 0, display: 'flex' }}>
              <X size={13} />
            </button>
          )}
        </div>

        {searchOpen && searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
            background: 'var(--surface-raised)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10, overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', zIndex: 100,
          }}>
            {searchResults.map((e: any, i: number) => (
              <div key={i}
                onClick={() => { setSearchOpen(false); setSearchQuery(''); router.push(role === 'employe' ? '/employe/profil' : '/hr/employes'); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', cursor: 'pointer',
                  borderBottom: i < searchResults.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none',
                }}
                onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
              >
                <div style={{ width: 30, height: 30, borderRadius: 7, background: 'rgba(15,163,224,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, color: '#45B9E9', flexShrink: 0 }}>
                  {e.prenom?.[0]}{e.nom?.[0]}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0C2436', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.prenom} {e.nom}</div>
                  <div style={{ fontSize: '0.68rem', color: '#9DB3C2' }}>{e.poste} · {e.matricule}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {searchOpen && searchQuery && searchResults.length === 0 && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
            background: 'var(--surface-raised)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 10, padding: '16px', textAlign: 'center',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)', zIndex: 100,
          }}>
            <div style={{ fontSize: '0.78rem', color: '#9DB3C2' }}>No employee found</div>
          </div>
        )}
      </div>

      <div style={{ flex: 1 }} />

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>

        {/* Clock */}
        <div style={{ fontSize: '0.78rem', color: '#6B879B', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: '#34546A', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{time}</span>
          <span style={{ color: '#9DB3C2' }}>|</span>
          <span>{dateStr}</span>
        </div>

        {/* Settings */}
        <button onClick={() => router.push(settingsPath)} title="Settings" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6B879B', padding: 6, borderRadius: 8, display: 'flex', transition: 'background 0.15s, color 0.15s' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(12,36,54,0.04)'; e.currentTarget.style.color = '#0C2436'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#6B879B'; }}
        >
          <Settings size={17} />
        </button>

        {/* Bell */}
        <div ref={bellRef} style={{ position: 'relative' }}>
          <button onClick={() => setBellOpen(o => !o)} style={{
            position: 'relative', background: bellOpen ? 'rgba(12,36,54,0.04)' : 'none',
            border: 'none', cursor: 'pointer', color: bellOpen ? '#0C2436' : '#6B879B',
            padding: 6, borderRadius: 8, display: 'flex', transition: 'background 0.15s, color 0.15s',
          }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(12,36,54,0.04)'; e.currentTarget.style.color = '#0C2436'; }}
            onMouseLeave={e => { if (!bellOpen) { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#6B879B'; } }}
          >
            <Bell size={17} />
            {unreadCnt > 0 && (
              <span style={{
                position: 'absolute', top: 2, right: 2,
                minWidth: 16, height: 16, borderRadius: 8,
                background: '#da3633', border: '1.5px solid #F2F7FB',
                fontSize: '0.58rem', fontWeight: 700, color: 'white',
                display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 3px',
              }}>{unreadCnt > 9 ? '9+' : unreadCnt}</span>
            )}
          </button>

          {bellOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', right: 0, width: 320,
              background: 'var(--surface-raised)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12, overflow: 'hidden', boxShadow: '0 12px 32px rgba(0,0,0,0.5)', zIndex: 100,
            }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Notifications</div>
                {unreadCnt > 0 && (
                  <span style={{ fontSize: '0.65rem', background: 'rgba(248,81,73,0.15)', color: '#f85149', padding: '2px 8px', borderRadius: 20, fontWeight: 700 }}>
                    {unreadCnt} unread
                  </span>
                )}
              </div>
              <div style={{ maxHeight: 310, overflowY: 'auto' }}>
                {alertes.length === 0 ? (
                  <div style={{ padding: '28px 16px', textAlign: 'center' }}>
                    <CheckCircle2 size={26} color="#3fb950" style={{ margin: '0 auto 8px', display: 'block' }} />
                    <div style={{ fontSize: '0.78rem', color: '#9DB3C2' }}>All clear — no alerts</div>
                  </div>
                ) : alertes.map((a: any, i: number) => {
                  const nc = NIV_CFG[a.niveau] || NIV_CFG.Info;
                  return (
                    <div key={i}
                      style={{
                        padding: '12px 16px',
                        borderBottom: i < alertes.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none',
                        background: a.est_lue ? 'transparent' : 'rgba(15,163,224,0.04)',
                        cursor: 'pointer', transition: 'background 0.1s',
                      }}
                      onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                      onMouseLeave={ev => (ev.currentTarget.style.background = a.est_lue ? 'transparent' : 'rgba(15,163,224,0.04)')}
                      onClick={() => { setBellOpen(false); router.push(alertsPath); }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                        <span style={{ background: nc.bg, color: nc.color, fontSize: '0.62rem', fontWeight: 700, padding: '2px 7px', borderRadius: 20 }}>{a.niveau}</span>
                        {!a.est_lue && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#0FA3E0' }} />}
                      </div>
                      <div style={{ fontSize: '0.77rem', color: '#34546A', lineHeight: 1.45, overflow: 'hidden', maxHeight: '2.9em' }}>
                        {a.message}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{ padding: '10px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                <button onClick={() => { setBellOpen(false); router.push(alertsPath); }} style={{
                  width: '100%', background: 'rgba(12,36,54,0.04)', border: '1px solid var(--border)',
                  borderRadius: 7, padding: '7px', fontSize: '0.75rem', color: '#6B879B', cursor: 'pointer', fontWeight: 600,
                }}>
                  View all alerts
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{ width: 1, height: 28, background: 'rgba(12,36,54,0.04)' }} />

        {/* User */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: avatarBg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 700, fontSize: '0.68rem', flexShrink: 0 }}>
            {initials}
          </div>
          <div style={{ lineHeight: 1.3 }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#0C2436' }}>
              {emp.prenom ? `${emp.prenom} ${emp.nom}` : roleLabel}
            </div>
            <div style={{ fontSize: '0.63rem', color: '#6B879B' }}>{roleLabel}</div>
          </div>
          <button onClick={logout} title="Logout" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(255,255,255,0.2)', padding: 5, borderRadius: 7, display: 'flex', transition: 'color 0.15s, background 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#f85149'; e.currentTarget.style.background = 'rgba(248,81,73,0.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.2)'; e.currentTarget.style.background = 'none'; }}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </header>
  );
}
