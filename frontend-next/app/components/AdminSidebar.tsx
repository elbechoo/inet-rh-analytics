'use client';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { LayoutDashboard, Users, Building2, Settings, ScrollText, LogOut, ShieldCheck } from 'lucide-react';
import { useRipple } from './motion';
import { LogoWordmark } from './Logo';
import { logout as doLogout } from './../lib/api';

const navItems = [
  { label: 'Dashboard',     href: '/admin/dashboard', Icon: LayoutDashboard },
  { label: 'Users',         href: '/admin/users',     Icon: Users },
  { label: 'Departments',   href: '/admin/depts',     Icon: Building2 },
  { label: 'Configuration', href: '/admin/config',    Icon: Settings },
  { label: 'Audit Trail',   href: '/admin/audit',     Icon: ShieldCheck },
  { label: 'System Logs',   href: '/admin/logs',      Icon: ScrollText },
];

export default function AdminSidebar() {
  const pathname = usePathname();
  const ripple = useRipple();
  const router   = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const u = localStorage.getItem('inet_user');
    if (u) { try { setUser(JSON.parse(u)); } catch {} }
  }, []);

  const logout = async () => {
    await doLogout();
    router.push('/');
  };

  const emp      = user?.employe || {};
  const initials = emp.prenom && emp.nom ? `${emp.prenom[0]}${emp.nom[0]}`.toUpperCase() : 'AD';

  return (
    <aside className="app-sidebar" style={{
      width: 244, minHeight: '100vh', background: 'var(--nav)',
      display: 'flex', flexDirection: 'column',
      position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 100,
      borderRight: '1px solid rgba(12,36,54,0.04)',
    }}>
      <div style={{ padding: '18px 16px 14px', flexShrink: 0 }}>
        <LogoWordmark size={40} subtitle="Administration" />
      </div>

      <div style={{ height:1, background:"rgba(12,36,54,0.04)", margin: '0 16px 6px' }} />

      <nav style={{ flex: 1, padding: '0 14px', overflowY: 'auto', scrollbarWidth: 'none' }}>
        <div className="t-label" style={{ padding: '16px 4px 7px', fontSize: '0.57rem', opacity: 0.6 }}>
          Administration
        </div>
        {navItems.map(item => {
          const active = pathname.startsWith(item.href);
          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              onMouseDown={ripple}
              className={`nav-item${active ? ' nav-item-active' : ''}`}
            >
              <item.Icon size={16} style={{ flexShrink: 0, color: active ? 'var(--brand-300)' : 'inherit' }} />
              <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div style={{ height:1, background:"rgba(12,36,54,0.04)", margin: '0 16px 10px' }} />

      <div style={{ padding: '0 14px 16px', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 'var(--radius-sm)',
          background: 'var(--grad-brand)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontWeight: 700, fontSize: '0.72rem', flexShrink: 0,
        }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: 'var(--ink)', fontWeight: 600, fontSize: '0.77rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {emp.prenom} {emp.nom}
          </div>
          <div style={{ fontSize: "0.63rem", color: 'var(--muted)' }}>Administrator</div>
        </div>
        <button onClick={logout} title="Logout" className="btn-ghost" style={{ padding: 7 }}>
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  );
}
