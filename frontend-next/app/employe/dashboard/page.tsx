'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, Clock, XCircle, Timer, Umbrella, Calendar, ArrowRight, Zap, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface MonthStat { mois: string; presents: number; retards: number; absences: number; }

export default function EmployeeDashboard() {
  const [user,         setUser]         = useState<any>(null);
  const [pointage,     setPointage]     = useState<any>(null);
  const [solde,        setSolde]        = useState<any>({});
  const [conges,       setConges]       = useState<any[]>([]);
  const [alertes,      setAlertes]      = useState<any[]>([]);
  const [monthlyStats, setMonthlyStats] = useState<MonthStat[]>([]);
  const [loading,      setLoading]      = useState(true);
  const router = useRouter();

  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem('inet_user') || '{}');
      if (!u?.employe?.employe_id) { router.push('/'); return; }
      setUser(u);
      const id = u.employe.employe_id;
      Promise.all([
        fetch(`/api/pointages/stats/${id}`).then(r => r.json()).catch(() => ({})),
        fetch(`/api/conges/solde/${id}`).then(r => r.json()).catch(() => ({})),
        fetch(`/api/conges/${id}`).then(r => r.json()).catch(() => []),
        fetch(`/api/ai/alertes?employe_id=${id}&limit=5`).then(r => r.json()).catch(() => []),
        fetch(`/api/pointages/stats/monthly-range/${id}?months=6`).then(r => r.json()).catch(() => []),
      ]).then(([p, s, c, a, ms]) => {
        setPointage(p || {});
        setSolde(s || {});
        setConges(Array.isArray(c) ? c.slice(0, 5) : []);
        setAlertes(Array.isArray(a) ? a.slice(0, 4) : []);
        setMonthlyStats(Array.isArray(ms) ? ms : []);
        setLoading(false);
      });
    } catch { router.push('/'); }
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div className="spinner" />
    </div>
  );

  const emp    = user?.employe || {};
  const hour   = new Date().getHours();
  const greet  = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const sr     = solde.solde_restant ?? 0;
  const sa     = solde.solde_annuel ?? 30;
  const used   = solde.solde_utilise ?? 0;
  const pct    = sa ? Math.round(used / sa * 100) : 0;

  const statusCfg: Record<string, { bg: string; color: string; label: string }> = {
    'Approuvé':   { bg: 'rgba(46,160,67,0.2)',  color: '#3fb950', label: 'Approved' },
    'En attente': { bg: 'rgba(227,179,65,0.2)', color: '#e3b341', label: 'Pending'  },
    'Refusé':     { bg: 'rgba(248,81,73,0.2)',  color: '#f85149', label: 'Rejected' },
  };

  const kpis = [
    { label: 'Days Present', value: pointage?.nb_presents ?? 0,                          Icon: CheckCircle2, color: '#3fb950' },
    { label: 'Late',         value: pointage?.nb_retards  ?? 0,                          Icon: Clock,        color: '#e3b341' },
    { label: 'Absences',     value: pointage?.nb_absences ?? 0,                          Icon: XCircle,      color: '#f85149' },
    { label: 'Total Hours',  value: `${(pointage?.total_heures ?? 0).toFixed(0)}h`,      Icon: Timer,        color: '#45B9E9' },
  ];

  const attendancePct = (pointage?.nb_presents ?? 0) + (pointage?.nb_absences ?? 0) > 0
    ? Math.round((pointage.nb_presents / ((pointage.nb_presents || 0) + (pointage.nb_absences || 0))) * 100)
    : 0;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Hero banner */}
      <div style={{ background: 'linear-gradient(135deg,#1e1b4b 0%,#0A2C41 50%,#0A6E9C 100%)', borderRadius: 16, padding: '28px 32px', marginBottom: 22, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: -40, right: -40, width: 200, height: 200, borderRadius: '50%', background: 'rgba(12,36,54,0.04)' }} />
        <div style={{ position: 'absolute', bottom: -20, right: 80, width: 120, height: 120, borderRadius: '50%', background: 'rgba(12,36,54,0.04)' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative' }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)', marginBottom: 6, fontWeight: 500 }}>
              {new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 700, color: 'white', marginBottom: 4, letterSpacing: '-0.3px' }}>
              {greet}, {emp.prenom}
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.55)', margin: 0 }}>
              {emp.poste} &middot; {emp.matricule}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, padding: '6px 12px' }}>
              <Zap size={13} color="rgba(255,255,255,0.7)" />
              <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.72rem', fontWeight: 600 }}>Employee</span>
            </div>
            {attendancePct > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)', borderRadius: 8, padding: '6px 12px' }}>
                <TrendingUp size={13} color="#3fb950" />
                <span style={{ color: '#3fb950', fontSize: '0.72rem', fontWeight: 700 }}>{attendancePct}% attendance</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 22 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', transition: 'transform 0.15s, border-color 0.15s' }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)'; }}
          >
            <div style={{ width: 36, height: 36, borderRadius: 9, background: `${k.color}1a`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
              <k.Icon size={18} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.9rem', fontWeight: 700, color: k.color, lineHeight: 1, marginBottom: 4 }}>{k.value}</div>
            <div style={{ fontSize: '0.68rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Monthly Attendance Chart */}
      {monthlyStats.length > 0 && (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', marginBottom: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0C2436' }}>My Attendance — Last 6 Months</div>
              <div style={{ fontSize: '0.72rem', color: '#9DB3C2', marginTop: 2 }}>Present days, late arrivals, and absences per month</div>
            </div>
            <div style={{ display: 'flex', gap: 14 }}>
              {[{ label: 'Present', color: '#3fb950' }, { label: 'Late', color: '#e3b341' }, { label: 'Absent', color: '#f85149' }].map(l => (
                <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: l.color }} />
                  <span style={{ fontSize: '0.68rem', color: '#6B879B' }}>{l.label}</span>
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={monthlyStats} margin={{ top: 0, right: 8, left: -20, bottom: 0 }} barGap={3}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(12,36,54,0.04)" vertical={false} />
              <XAxis dataKey="mois" tick={{ fill: '#9DB3C2', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#9DB3C2', fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-raised)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: '0.75rem' }}
                labelStyle={{ color: '#0C2436', fontWeight: 600 }}
              />
              <Bar dataKey="presents" name="Present" fill="#3fb950" radius={[3, 3, 0, 0]} maxBarSize={22} />
              <Bar dataKey="retards"  name="Late"    fill="#e3b341" radius={[3, 3, 0, 0]} maxBarSize={22} />
              <Bar dataKey="absences" name="Absent"  fill="#f85149" radius={[3, 3, 0, 0]} maxBarSize={22} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>

        {/* Leave Balance */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '22px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Leave Balance</div>
              <div style={{ fontSize: '0.70rem', color: '#9DB3C2', marginTop: 2 }}>{new Date().getFullYear()}</div>
            </div>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(69,185,233,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Umbrella size={17} color="#45B9E9" />
            </div>
          </div>
          <div style={{ textAlign: 'center', padding: '8px 0 20px' }}>
            <div style={{ fontSize: '4rem', fontWeight: 700, color: '#45B9E9', lineHeight: 1 }}>{sr}</div>
            <div style={{ fontSize: '0.80rem', color: '#9DB3C2', marginTop: 6 }}>days remaining</div>
          </div>
          <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 99, height: 8, marginBottom: 14, overflow: 'hidden' }}>
            <div style={{ background: 'linear-gradient(90deg,#0FA3E0,#0B87BE)', width: `${pct}%`, height: 8, borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-around' }}>
            {[
              { label: 'Total', value: `${sa}d`, color: '#0C2436' },
              { label: 'Used',  value: `${used}d`, color: '#f85149' },
              { label: 'Left',  value: `${sr}d`, color: '#3fb950' },
            ].map((s, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: '0.63rem', color: '#9DB3C2', fontWeight: 700, textTransform: 'uppercase', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Leave Requests */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '22px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Recent Leave Requests</div>
              <div style={{ fontSize: '0.70rem', color: '#9DB3C2', marginTop: 2 }}>{conges.length} total</div>
            </div>
            <Link href="/employe/demandes" style={{ fontSize: '0.72rem', color: '#45B9E9', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 600 }}>
              View all <ArrowRight size={11} />
            </Link>
          </div>
          {conges.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '28px 0' }}>
              <CheckCircle2 size={28} color="#3fb950" style={{ margin: '0 auto 10px', display: 'block' }} />
              <div style={{ fontSize: '0.82rem', color: '#3fb950', fontWeight: 600 }}>No requests yet</div>
              <Link href="/employe/demandes" style={{ fontSize: '0.73rem', color: '#45B9E9', textDecoration: 'none', display: 'block', marginTop: 6 }}>Submit your first request</Link>
            </div>
          ) : conges.map((c: any, i: number) => {
            const st = statusCfg[c.statut] || { bg: 'rgba(12,36,54,0.04)', color: '#6B879B', label: c.statut };
            return (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: i < conges.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none' }}>
                <div>
                  <div style={{ fontSize: '0.80rem', fontWeight: 600, color: '#0C2436' }}>{c.type_conge}</div>
                  <div style={{ fontSize: '0.70rem', color: '#9DB3C2', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Calendar size={10} />
                    {c.date_debut} — {c.date_fin}
                  </div>
                </div>
                <span style={{ background: st.bg, color: st.color, padding: '3px 10px', borderRadius: 20, fontSize: '0.67rem', fontWeight: 700, flexShrink: 0 }}>
                  {st.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Quick links */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '22px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 14 }}>Quick Access</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              { label: 'Attendance',    desc: 'Clock in / out',  href: '/employe/pointage',  color: '#3fb950', Icon: CheckCircle2 },
              { label: 'Leave Request', desc: 'Submit a request', href: '/employe/demandes',  color: '#45B9E9', Icon: Umbrella    },
              { label: 'My Training',   desc: 'Upcoming sessions',href: '/employe/formations',color: '#45B9E9', Icon: Calendar    },
              { label: 'My Profile',    desc: 'View details',    href: '/employe/profil',    color: '#22d3ee', Icon: Zap         },
            ].map((item, i) => (
              <Link key={i} href={item.href} style={{ textDecoration: 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: `${item.color}10`, border: `1px solid ${item.color}25`, borderRadius: 10, padding: '12px 14px', cursor: 'pointer', transition: 'all 0.15s' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = `${item.color}1a`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = `${item.color}10`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'; }}
                >
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: `${item.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <item.Icon size={16} style={{ color: item.color }} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: item.color }}>{item.label}</div>
                    <div style={{ fontSize: '0.65rem', color: '#9DB3C2' }}>{item.desc}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* AI Alerts */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '22px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 14 }}>AI Alerts — About Me</div>
          {alertes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '28px 0' }}>
              <CheckCircle2 size={30} color="#3fb950" style={{ margin: '0 auto 10px', display: 'block' }} />
              <div style={{ fontSize: '0.84rem', color: '#3fb950', fontWeight: 600 }}>All clear — no alerts</div>
              <div style={{ fontSize: '0.73rem', color: '#9DB3C2', marginTop: 4 }}>Your attendance looks great</div>
            </div>
          ) : alertes.map((a: any, i: number) => {
            const cfg: Record<string, any> = {
              Critique: { bar: '#f85149', badge: 'rgba(248,81,73,0.15)',  text: '#f85149' },
              Moyen:    { bar: '#e3b341', badge: 'rgba(227,179,65,0.15)', text: '#e3b341' },
              Info:     { bar: '#45B9E9', badge: 'rgba(15,163,224,0.15)', text: '#45B9E9' },
            };
            const c = cfg[a.niveau] || cfg.Info;
            return (
              <div key={i} style={{ display: 'flex', gap: 12, padding: '10px 0', borderBottom: i < alertes.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none' }}>
                <div style={{ width: 3, height: 40, borderRadius: 99, background: c.bar, flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 500, color: '#34546A', marginBottom: 5, lineHeight: 1.4 }}>{a.message?.slice(0, 80)}{(a.message?.length ?? 0) > 80 ? '...' : ''}</div>
                  <span style={{ background: c.badge, color: c.text, fontSize: '0.62rem', fontWeight: 700, padding: '2px 8px', borderRadius: 20 }}>{a.niveau}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
