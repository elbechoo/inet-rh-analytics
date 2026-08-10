'use client';
import { useRouter, usePathname } from 'next/navigation';
import { LayoutDashboard, Clock, FileText, GraduationCap, User, LogOut } from 'lucide-react';
import { useRipple } from './motion';
import { LogoWordmark } from './Logo';
import { logout as doLogout } from './../lib/api';

const NAV_ITEMS: any[] = [
  { section: 'My Space' },
  { label: 'Dashboard',   icon: LayoutDashboard, path: '/employe/dashboard' },
  { label: 'Attendance',  icon: Clock,           path: '/employe/pointage' },
  { label: 'My Requests', icon: FileText,        path: '/employe/demandes' },
  { label: 'Training',    icon: GraduationCap,   path: '/employe/formations' },
  { label: 'My Profile',  icon: User,            path: '/employe/profil' },
];

export default function EmployeeSidebar() {
  const router   = useRouter();
  const pathname = usePathname();
  const ripple = useRipple();

  let user: any = null;
  if (typeof window !== 'undefined') {
    try { user = JSON.parse(localStorage.getItem('inet_user') || '{}'); } catch {}
  }
  const emp      = user?.employe || {};
  const initials = emp.prenom && emp.nom ? `${emp.prenom[0]}${emp.nom[0]}`.toUpperCase() : 'EMP';

  async function logout() {
    await doLogout();
    router.push('/');
  }

  return (
    <aside className="app-sidebar" style={{
      width: 244, minWidth: 244,
      background: 'var(--nav)',
      height: '100vh', position: 'fixed', left: 0, top: 0,
      display: 'flex', flexDirection: 'column',
      zIndex: 50, borderRight: '1px solid rgba(12,36,54,0.04)',
      overflow: 'hidden',
    }}>
      <div style={{ padding: '18px 16px 14px', flexShrink: 0 }}>
        <LogoWordmark size={40} subtitle="Espace Employé" />
      </div>

      <div style={{ height:1, background:"rgba(12,36,54,0.04)", margin: '0 16px 6px' }} />

      <nav style={{ flex: 1, overflowY: 'auto', padding: '0 14px', scrollbarWidth: 'none' }}>
        {NAV_ITEMS.map((item: any, i: number) => {
          if (item.section) return (
            <div key={i} className="t-label" style={{ padding: '16px 4px 7px', fontSize: '0.57rem', opacity: 0.6 }}>
              {item.section}
            </div>
          );
          const active = pathname === item.path;
          const Icon   = item.icon;
          return (
            <button
              key={i}
              onClick={() => router.push(item.path)}
              onMouseDown={ripple}
              className={`nav-item${active ? ' nav-item-active' : ''}`}
            >
              <Icon size={16} style={{ flexShrink: 0, color: active ? 'var(--brand-300)' : 'inherit' }} />
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
          <div style={{ fontSize: "0.63rem", color: 'var(--muted)' }}>Employee</div>
        </div>
        <button onClick={logout} title="Logout" className="btn-ghost" style={{ padding: 7 }}>
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  );
}
