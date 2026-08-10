'use client';
import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  LayoutDashboard, Clock, FileText, GraduationCap,
  Users, CheckSquare, Calendar, BarChart2, AlertTriangle,
  ChevronLeft, ChevronRight, LogOut, CalendarDays,
} from 'lucide-react';
import { useRipple } from './motion';
import { LogoWordmark, LogoMark } from './Logo';
import { logout as doLogout } from './../lib/api';

interface NavItem {
  section?: string;
  label?: string;
  icon?: React.ElementType;
  path?: string;
}

const NAV_ITEMS: NavItem[] = [
  { section: 'My Space' },
  { label: 'Dashboard',    icon: LayoutDashboard, path: '/hr/dashboard' },
  { label: 'Attendance',   icon: Clock,           path: '/hr/pointage' },
  { label: 'My Requests',  icon: FileText,        path: '/hr/demandes' },
  { label: 'My Training',  icon: GraduationCap,   path: '/hr/formations-perso' },
  { section: 'Administration' },
  { label: 'Employees',    icon: Users,           path: '/hr/employes' },
  { label: 'Validations',  icon: CheckSquare,     path: '/hr/validations' },
  { label: 'Absences',     icon: Calendar,        path: '/hr/absences' },
  { label: 'Statistics',   icon: BarChart2,       path: '/hr/stats' },
  { label: 'AI Alerts',    icon: AlertTriangle,   path: '/hr/alertes' },
  { label: 'Training',     icon: GraduationCap,   path: '/hr/formations' },
  { label: 'Holidays',     icon: CalendarDays,    path: '/hr/jours-feries' },
];

interface SidebarProps {
  collapsed?: boolean;
  onCollapse?: (v: boolean) => void;
}

export default function Sidebar({ collapsed: collapsedProp, onCollapse }: SidebarProps = {}) {
  const router   = useRouter();
  const pathname = usePathname();
  const ripple = useRipple();
  const [collapsed, setCollapsed] = useState(collapsedProp ?? false);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    onCollapse?.(next);
  }

  let user: any = null;
  if (typeof window !== 'undefined') {
    try { user = JSON.parse(localStorage.getItem('inet_user') || '{}'); } catch {}
  }
  const emp      = user?.employe || {};
  const initials = emp.prenom && emp.nom ? `${emp.prenom[0]}${emp.nom[0]}`.toUpperCase() : 'RH';
  const role     = user?.role || 'rh';

  async function logout() {
    await doLogout();
    router.push('/');
  }

  return (
    <aside className="app-sidebar" style={{
      width: collapsed ? 72 : 244,
      minWidth: collapsed ? 72 : 244,
      background: 'var(--nav)',
      height: '100vh',
      position: 'fixed',
      left: 0, top: 0,
      display: 'flex',
      flexDirection: 'column',
      transition: 'width var(--dur) var(--ease-out)',
      zIndex: 50,
      borderRight: '1px solid rgba(12,36,54,0.04)',
      overflow: 'hidden',
    }}>

      {/* Logo + collapse toggle */}
      <div style={{
        padding: '18px 16px 14px',
        display: 'flex', alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        flexShrink: 0, gap: 8,
      }}>
        {collapsed ? <LogoMark size={34} /> : <LogoWordmark size={40} subtitle="Système de Gestion RH" />}
        {!collapsed && (
          <button onClick={toggle} className="btn-ghost" style={{ padding: 6 }} title="Collapse">
            <ChevronLeft size={14} />
          </button>
        )}
      </div>

      {collapsed && (
        <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: 10, flexShrink: 0 }}>
          <button onClick={toggle} className="btn-ghost" style={{ padding: 6 }} title="Expand">
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      <div style={{ height:1, background:"rgba(12,36,54,0.04)", margin: '0 16px 6px' }} />

      {/* Navigation */}
      <nav style={{
        flex: 1, overflowY: 'auto', overflowX: 'hidden',
        padding: collapsed ? '0 10px' : '0 14px', scrollbarWidth: 'none',
      }}>
        {NAV_ITEMS.map((item, i) => {
          if (item.section) {
            if (collapsed) return <div key={i} style={{ height: 14 }} />;
            return (
              <div key={i} className="t-label" style={{ padding: '16px 4px 7px', fontSize: '0.57rem', opacity: 0.6 }}>
                {item.section}
              </div>
            );
          }
          const active = pathname === item.path || (item.path ? pathname.startsWith(item.path + '/') : false);
          const Icon   = item.icon!;
          return (
            <button
              key={i}
              onClick={() => router.push(item.path!)}
              title={collapsed ? item.label : ''}
              onMouseDown={ripple}
              className={`nav-item${active ? ' nav-item-active' : ''}`}
              style={collapsed ? { justifyContent: 'center', padding: '10px 0', gap: 0 } : undefined}
            >
              <Icon size={16} style={{ flexShrink: 0, color: active ? 'var(--brand-300)' : 'inherit' }} />
              {!collapsed && <span style={{ flex: 1, textAlign: 'left' }}>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      <div style={{ height:1, background:"rgba(12,36,54,0.04)", margin: '0 16px 10px' }} />

      {/* User */}
      <div style={{
        padding: collapsed ? '0 10px 16px' : '0 14px 16px',
        display: 'flex', alignItems: 'center', gap: 10,
        justifyContent: collapsed ? 'center' : 'flex-start', flexShrink: 0,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 'var(--radius-sm)',
          background: 'var(--grad-brand)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontWeight: 700, fontSize: '0.72rem', flexShrink: 0,
        }}>
          {initials}
        </div>
        {!collapsed && (
          <>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: 'var(--ink)', fontWeight: 600, fontSize: '0.77rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {emp.prenom} {emp.nom}
              </div>
              <div style={{ fontSize: "0.63rem", color: 'var(--muted)' }}>
                {role === 'admin' ? 'Administrator' : 'HR Manager'}
              </div>
            </div>
            <button onClick={logout} title="Logout" className="btn-ghost" style={{ padding: 7 }}>
              <LogOut size={15} />
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
