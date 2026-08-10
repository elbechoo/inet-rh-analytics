'use client';
import { useEffect, useState } from 'react';
import { Users, UserCheck, Building2, Shield, Briefcase, AlertTriangle, Settings, FileText, Database, Activity, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { authFetch } from '@/app/lib/api';
import type { Departement, Utilisateur } from '@/app/types/api';

interface AdminStats {
  nb_users: number; nb_employes: number; nb_depts: number;
  nb_admins: number; nb_rh: number; nb_alertes_non_lues: number;
}


const QUICK_LINKS = [
  { label: 'Manage Users',  desc: 'Create & edit accounts', href: '/admin/users',  Icon: Users,    color: '#45B9E9', bg: 'rgba(15,163,224,0.12)'  },
  { label: 'Departments',   desc: 'Org structure',          href: '/admin/depts',  Icon: Building2, color: '#45B9E9', bg: 'rgba(69,185,233,0.12)' },
  { label: 'Configuration', desc: 'System settings',        href: '/admin/config', Icon: Settings,  color: '#e3b341', bg: 'rgba(227,179,65,0.12)'  },
  { label: 'System Logs',   desc: 'Audit & events',         href: '/admin/logs',   Icon: FileText,  color: '#f85149', bg: 'rgba(248,81,73,0.12)'   },
];

export default function AdminDashboard() {
  const [stats,   setStats]   = useState<AdminStats | null>(null);
  const [depts,   setDepts]   = useState<Departement[]>([]);
  const [loading, setLoading] = useState(true);
  const [user,    setUser]    = useState<Utilisateur | null>(null);

  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem('inet_user') || '{}')); } catch {}
    Promise.all([
      authFetch('/api/admin/stats').then(r => r.json()).catch(() => null),
      authFetch('/api/admin/depts').then(r => r.json()).catch(() => []),
    ]).then(([s, d]) => {
      setStats(s);
      setDepts(Array.isArray(d) ? d : []);
      setLoading(false);
    });
  }, []);

  const hour  = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const emp   = user?.employe;

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div className="spinner" />
    </div>
  );

  const kpiCards = stats ? [
    { label: 'Total Users',      value: stats.nb_users,            Icon: Users,         color: '#45B9E9', dimColor: 'rgba(15,163,224,0.15)' },
    { label: 'Active Employees', value: stats.nb_employes,         Icon: UserCheck,     color: '#22d3ee', dimColor: 'rgba(34,211,238,0.15)' },
    { label: 'Departments',      value: stats.nb_depts,            Icon: Building2,     color: '#45B9E9', dimColor: 'rgba(69,185,233,0.15)' },
    { label: 'Admins',           value: stats.nb_admins,           Icon: Shield,        color: '#f85149', dimColor: 'rgba(248,81,73,0.15)' },
    { label: 'HR Managers',      value: stats.nb_rh,               Icon: Briefcase,     color: '#e3b341', dimColor: 'rgba(227,179,65,0.15)' },
    { label: 'Unread Alerts',    value: stats.nb_alertes_non_lues, Icon: AlertTriangle, color: '#f85149', dimColor: 'rgba(248,81,73,0.15)' },
  ] : [];

  const totalUsers = (stats?.nb_admins || 0) + (stats?.nb_rh || 0) + ((stats?.nb_employes || 0));
  const roleDistrib = totalUsers > 0 ? [
    { label: 'Admins',   count: stats?.nb_admins   || 0, color: '#f85149', pct: Math.round((stats?.nb_admins   || 0) / totalUsers * 100) },
    { label: 'HR',       count: stats?.nb_rh       || 0, color: '#e3b341', pct: Math.round((stats?.nb_rh       || 0) / totalUsers * 100) },
    { label: 'Employees', count: stats?.nb_employes || 0, color: '#3fb950', pct: Math.round((stats?.nb_employes || 0) / totalUsers * 100) },
  ] : [];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <div style={{ fontSize: '0.72rem', color: '#9DB3C2', marginBottom: 4, fontWeight: 500 }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0C2436', marginBottom: 3, letterSpacing: '-0.3px' }}>
            {greet}, {emp?.prenom || 'Admin'}
          </h1>
          <p style={{ fontSize: '0.82rem', color: '#6B879B' }}>System administration overview</p>
        </div>
        <div style={{ background: 'linear-gradient(135deg,#17557A,#0F3E5A)', color: 'white', padding: '6px 14px', borderRadius: 8, fontSize: '0.72rem', fontWeight: 700, boxShadow: '0 2px 8px rgba(23,85,122,0.4)' }}>
          Administrator
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 22 }}>
        {kpiCards.map((card, i) => (
          <div key={i} style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', display: 'flex', alignItems: 'center', gap: 16, transition: 'border-color 0.15s, transform 0.15s', position: 'relative', overflow: 'hidden' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)'; e.currentTarget.style.transform = 'translateY(0)'; }}
          >
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: card.color, opacity: 0.6 }} />
            <div style={{ width: 48, height: 48, borderRadius: 12, background: card.dimColor, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <card.Icon size={22} style={{ color: card.color }} />
            </div>
            <div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: card.color, lineHeight: 1 }}>{card.value ?? '—'}</div>
              <div style={{ fontSize: '0.75rem', color: '#6B879B', marginTop: 3, fontWeight: 500 }}>{card.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Body grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 18 }}>

        {/* LEFT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Quick Links */}
          <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 14 }}>Quick Access</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
              {QUICK_LINKS.map(link => (
                <Link key={link.href} href={link.href} style={{ textDecoration: 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14, background: link.bg, border: `1px solid ${link.color}25`, borderRadius: 12, padding: '16px 18px', cursor: 'pointer', transition: 'all 0.15s' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = link.bg.replace('0.12)', '0.22)'); (e.currentTarget as HTMLDivElement).style.borderColor = `${link.color}50`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = link.bg; (e.currentTarget as HTMLDivElement).style.borderColor = `${link.color}25`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'; }}
                  >
                    <div style={{ width: 42, height: 42, borderRadius: 10, background: `${link.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <link.Icon size={20} style={{ color: link.color }} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: link.color }}>{link.label}</div>
                      <div style={{ fontSize: '0.70rem', color: '#9DB3C2', marginTop: 2 }}>{link.desc}</div>
                    </div>
                    <ArrowRight size={14} color={link.color} style={{ marginLeft: 'auto', opacity: 0.6 }} />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Departments */}
          {depts.length > 0 && (
            <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Building2 size={14} color="#45B9E9" />
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Departments ({depts.length})</span>
                </div>
                <Link href="/admin/depts" style={{ fontSize: '0.72rem', color: '#45B9E9', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 600 }}>
                  Manage <ArrowRight size={11} />
                </Link>
              </div>
              {depts.slice(0, 5).map((d: any, i: number) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '11px 20px', borderBottom: i < Math.min(depts.length, 5) - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none', transition: 'background 0.1s' }}
                  onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                  onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#45B9E9', flexShrink: 0 }} />
                    <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0C2436' }}>{d.nom_departement}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Users size={12} color="#9DB3C2" />
                    <span style={{ fontSize: '0.75rem', color: '#6B879B' }}>{d.nb_employes ?? '—'} employees</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* System Status */}
          <div style={{ background: 'linear-gradient(135deg,#F8FBFE,#FFFFFF)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Activity size={14} color="#3fb950" />
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>System Status</span>
              <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#3fb950', boxShadow: '0 0 6px #3fb950' }} />
                <span style={{ fontSize: '0.65rem', color: '#3fb950', fontWeight: 700 }}>ONLINE</span>
              </div>
            </div>
            {[
              { label: 'API Server',  status: 'Operational', color: '#3fb950' },
              { label: 'Database',    status: 'Connected',   color: '#3fb950' },
              { label: 'AI Engine',   status: 'Active',      color: '#3fb950' },
              { label: 'Scheduler',   status: 'Running',     color: '#3fb950' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < 3 ? '1px solid rgba(12,36,54,0.04)' : 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <Database size={12} color="#9DB3C2" />
                  <span style={{ fontSize: '0.76rem', color: '#6B879B' }}>{s.label}</span>
                </div>
                <span style={{ background: `${s.color}18`, color: s.color, fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px', borderRadius: 20 }}>{s.status}</span>
              </div>
            ))}
          </div>

          {/* Role Distribution */}
          <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 16 }}>Role Distribution</div>
            {roleDistrib.map((r, i) => (
              <div key={i} style={{ marginBottom: i < roleDistrib.length - 1 ? 12 : 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                  <span style={{ fontSize: '0.75rem', color: '#6B879B' }}>{r.label}</span>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: r.color }}>{r.count} ({r.pct}%)</span>
                </div>
                <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 99, height: 6, overflow: 'hidden' }}>
                  <div style={{ background: r.color, width: `${r.pct}%`, height: 6, borderRadius: 99, transition: 'width 0.8s ease' }} />
                </div>
              </div>
            ))}
          </div>

          {/* Alert summary */}
          {(stats?.nb_alertes_non_lues ?? 0) > 0 && (
            <Link href="/hr/alertes" style={{ textDecoration: 'none' }}>
              <div style={{ background: 'rgba(248,81,73,0.08)', borderRadius: 'var(--radius-lg)', padding: '16px 20px', border: '1px solid rgba(248,81,73,0.2)', cursor: 'pointer', transition: 'all 0.15s' }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'rgba(248,81,73,0.12)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'rgba(248,81,73,0.08)'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <AlertTriangle size={18} color="#f85149" />
                  <div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f85149' }}>{stats?.nb_alertes_non_lues} unread AI alerts</div>
                    <div style={{ fontSize: '0.70rem', color: '#9DB3C2', marginTop: 2 }}>Click to review in HR panel</div>
                  </div>
                  <ArrowRight size={14} color="#f85149" style={{ marginLeft: 'auto' }} />
                </div>
              </div>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
