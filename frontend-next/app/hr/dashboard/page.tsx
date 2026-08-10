'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Users, UserCheck, Clock, Umbrella, AlertTriangle, ArrowRight, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { AnimatedNumber, Reveal, useRipple } from '@/app/components/motion';

/* Report palette — the logo azure leads, the mark's navy is the second series. */
const BLUE = '#0FA3E0', TEAL = '#12A594', SKY = '#17557A', AMBER = '#F59E0B', RED = '#DC2626';
const SERIES = [BLUE, TEAL, SKY, '#45B9E9', AMBER, '#0B87BE'];

async function api(path: string) {
  try {
    const r = await fetch(`/api${path}`, { credentials: 'include' });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

function ChartTip({ active, payload, label, suffix = '' }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border-2)', borderRadius: 10,
      padding: '9px 12px', boxShadow: 'var(--shadow-md)', fontSize: '.78rem',
    }}>
      {label !== undefined && (
        <div style={{ fontWeight: 620, color: 'var(--ink)', marginBottom: 5 }}>{label}</div>
      )}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 2 }}>
          <span className="dot" style={{ background: p.color || p.payload?.fill }} />
          <span style={{ color: 'var(--muted)' }}>{p.name}</span>
          <strong className="t-num" style={{ marginLeft: 'auto', color: 'var(--ink)' }}>
            {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}{suffix}
          </strong>
        </div>
      ))}
    </div>
  );
}

export default function HRDashboard() {
  const [employes, setEmployes]     = useState<any[]>([]);
  const [pointages, setPointages]   = useState<any[]>([]);
  const [conges, setConges]         = useState<any[]>([]);
  const [alertes, setAlertes]       = useState<any[]>([]);
  const [evolution, setEvolution]   = useState<any[]>([]);
  const [deptStats, setDeptStats]   = useState<any[]>([]);
  const [congeTypes, setCongeTypes] = useState<any[]>([]);
  const [risk, setRisk]             = useState<any[] | null>(null);
  const [user, setUser]             = useState<any>(null);
  const [loaded, setLoaded]         = useState(false);
  const ripple = useRipple();

  // Heavy aggregates load once; the live figures re-poll so the dashboard moves
  // on its own while data arrives (see demo/live_feed.py).
  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem('inet_user') || '{}')); } catch {}
    api('/employes/').then(d => { setEmployes(d || []); setLoaded(true); });
    api('/pointages/stats/evolution').then(d => setEvolution(Array.isArray(d) ? d : []));
    api('/pointages/kpis/departement').then(d => setDeptStats(Array.isArray(d) ? d : []));
    api('/conges/stats/par-type').then(d => setCongeTypes(Array.isArray(d) ? d : []));
    api('/ai/employes-a-risque').then(d => setRisk(Array.isArray(d) ? d : []));
  }, []);

  useEffect(() => {
    let alive = true;
    const pull = () => {
      if (document.hidden) return;                    // don't poll a hidden tab
      api('/pointages/today').then(d => { if (alive) setPointages(d || []); });
      api('/conges/en-attente/all').then(d => { if (alive) setConges(d || []); });
      api('/ai/alertes?limit=8').then(d => { if (alive) setAlertes(d || []); });
    };
    pull();
    const id = window.setInterval(pull, 8000);
    document.addEventListener('visibilitychange', pull);
    return () => {
      alive = false;
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', pull);
    };
  }, []);

  const total   = employes.length;
  const present = pointages.filter((p: any) => ['Présent', 'Present'].includes(p.statut)).length;
  const late    = pointages.filter((p: any) => p.statut === 'En retard').length;
  const unread  = alertes.filter((a: any) => !a.est_lue).length;
  const rate    = total ? Math.round((present / total) * 100) : 0;

  const deptPie = useMemo(() => deptStats
    .filter((d: any) => d.nb_employes > 0)
    .map((d: any) => ({ name: d.departement || d.nom_departement || '—', value: d.nb_employes }))
    .sort((a, b) => b.value - a.value).slice(0, 6), [deptStats]);

  const deptBar = useMemo(() => deptStats
    .filter((d: any) => d.nb_employes > 0)
    .map((d: any) => ({
      dept: String(d.departement || d.nom_departement || '—').slice(0, 14),
      absence: Number(d.taux_absenteisme ?? 0),
      late: Number(d.taux_retard ?? 0),
    }))
    .sort((a, b) => b.absence - a.absence).slice(0, 7), [deptStats]);

  const emp   = user?.employe;
  const hour  = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  const kpis = [
    { label: 'Total employees', value: total,         sub: 'active headcount',    icon: Users,         color: BLUE,  trend: null },
    { label: 'Present today',   value: present,       sub: `${rate}% attendance`, icon: UserCheck,     color: TEAL,  trend: rate >= 85 ? 'up' : 'down' },
    { label: 'Late arrivals',   value: late,          sub: 'today',               icon: Clock,         color: AMBER, trend: null },
    { label: 'Pending leave',   value: conges.length, sub: 'awaiting approval',   icon: Umbrella,      color: SKY,   trend: null },
    { label: 'AI alerts',       value: unread,        sub: 'unread',              icon: AlertTriangle, color: RED,   trend: unread > 0 ? 'down' : null },
  ];

  return (
    <div className="view-enter">

      <header style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <div>
          <div className="t-meta">
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
          <h1 className="page-title" style={{ marginTop: 3 }}>{greet}, {emp?.prenom || 'there'}</h1>
          <p className="page-subtitle">{total} employees · {present} present · {late} late</p>
        </div>
        <div style={{ display: 'flex', gap: 9 }}>
          {unread > 0 && (
            <Link href="/hr/alertes" className="badge badge-red" style={{ padding: '8px 13px', fontSize: '.76rem' }}>
              <AlertTriangle size={13} /> {unread} unread alert{unread > 1 ? 's' : ''}
            </Link>
          )}
          <Link href="/hr/employes" className="btn-primary">Manage employees <ArrowRight size={14} /></Link>
        </div>
      </header>

      <div className="stagger" style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))',
        gap: 14, marginBottom: 16,
      }}>
        {kpis.map(k => (
          <div key={k.label} onMouseDown={ripple}
               className="card card-hover kpi"
               style={{ ['--accent' as any]: k.color, padding: 18, position: 'relative', overflow: 'hidden', cursor: 'default' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="t-label">{k.label}</span>
              <span className="kpi-icon" style={{
                width: 30, height: 30, borderRadius: 9, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                background: `${k.color}14`, color: k.color,
              }}><k.icon size={15} /></span>
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--ink)', letterSpacing: '-.035em', marginTop: 8, lineHeight: 1.1 }}>
              {loaded
                ? <AnimatedNumber value={k.value} />
                : <span className="skeleton" style={{ display: 'inline-block', width: 48, height: 26, borderRadius: 6 }} />}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 3 }}>
              <span className="t-meta">{k.sub}</span>
              {k.trend === 'up'   && <ArrowUpRight   size={13} style={{ color: 'var(--green)' }} />}
              {k.trend === 'down' && <ArrowDownRight size={13} style={{ color: 'var(--red)' }} />}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1fr)', gap: 14, marginBottom: 16 }}>
        <div className="card animate-fadeup">
          <div className="card-head">
            <div>
              <div className="t-section">Attendance trend</div>
              <div className="t-meta" style={{ marginTop: 2 }}>Monthly presence and lateness rate</div>
            </div>
            <span className="badge badge-blue">This year</span>
          </div>
          {evolution.length === 0 ? <div className="skeleton" style={{ height: 260 }} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={evolution} margin={{ top: 6, right: 8, left: -22, bottom: 0 }}>
                <defs>
                  <linearGradient id="gPres" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={BLUE} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={BLUE} stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gLate" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={AMBER} stopOpacity={0.24} />
                    <stop offset="100%" stopColor={AMBER} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDF1F8" vertical={false} />
                <XAxis dataKey="mois" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false}
                       domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip content={<ChartTip suffix="%" />} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '.75rem', color: '#64748B' }} />
                <Area type="monotone" dataKey="taux_presence" name="Presence" stroke={BLUE} strokeWidth={2.4}
                      fill="url(#gPres)" dot={false} activeDot={{ r: 5 }} animationDuration={900} />
                <Area type="monotone" dataKey="taux_retard" name="Late" stroke={AMBER} strokeWidth={2.4}
                      fill="url(#gLate)" dot={false} activeDot={{ r: 5 }} animationDuration={900} animationBegin={150} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card animate-fadeup" style={{ animationDelay: '90ms' }}>
          <div className="card-head">
            <div>
              <div className="t-section">Headcount by department</div>
              <div className="t-meta" style={{ marginTop: 2 }}>Share of workforce</div>
            </div>
          </div>
          {deptPie.length === 0 ? <div className="skeleton" style={{ height: 200 }} /> : (
            <>
              <ResponsiveContainer width="100%" height={190}>
                <PieChart>
                  <Pie data={deptPie} cx="50%" cy="50%" innerRadius={52} outerRadius={80}
                       paddingAngle={3} dataKey="value" animationDuration={900}>
                    {deptPie.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} stroke="#fff" strokeWidth={2} />)}
                  </Pie>
                  <Tooltip content={<ChartTip />} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px 12px', marginTop: 6 }}>
                {deptPie.map((d, i) => (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                    <span className="dot" style={{ background: SERIES[i % SERIES.length] }} />
                    <span className="t-meta" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
                    <span className="t-meta t-num" style={{ marginLeft: 'auto', fontWeight: 600, color: 'var(--ink-2)' }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.4fr) minmax(0,1fr)', gap: 14, marginBottom: 16 }}>
        <div className="card animate-fadeup" style={{ animationDelay: '140ms' }}>
          <div className="card-head">
            <div>
              <div className="t-section">Absence and lateness by department</div>
              <div className="t-meta" style={{ marginTop: 2 }}>Rate in %</div>
            </div>
          </div>
          {deptBar.length === 0 ? <div className="skeleton" style={{ height: 240 }} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={deptBar} layout="vertical" margin={{ top: 0, right: 16, left: 6, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDF1F8" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                <YAxis type="category" dataKey="dept" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} width={104} />
                <Tooltip content={<ChartTip suffix="%" />} cursor={{ fill: 'rgba(15,163,224,.05)' }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '.75rem' }} />
                <Bar dataKey="absence" name="Absence rate" fill={BLUE} radius={[0, 5, 5, 0]} maxBarSize={13} animationDuration={800} />
                <Bar dataKey="late"    name="Late rate"    fill={TEAL} radius={[0, 5, 5, 0]} maxBarSize={13} animationDuration={800} animationBegin={120} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card animate-fadeup" style={{ animationDelay: '190ms' }}>
          <div className="card-head">
            <div>
              <div className="t-section">Leave by type</div>
              <div className="t-meta" style={{ marginTop: 2 }}>All-time requests</div>
            </div>
          </div>
          {congeTypes.length === 0 ? <div className="skeleton" style={{ height: 240 }} /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={congeTypes} margin={{ top: 6, right: 8, left: -24, bottom: 34 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDF1F8" vertical={false} />
                <XAxis dataKey="type" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false}
                       angle={-28} textAnchor="end" interval={0} />
                <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTip />} cursor={{ fill: 'rgba(15,163,224,.05)' }} />
                <Bar dataKey="count" name="Requests" radius={[6, 6, 0, 0]} maxBarSize={44} animationDuration={800}>
                  {congeTypes.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card animate-fadeup" style={{ animationDelay: '240ms', padding: 0, overflow: 'hidden' }}>
        <div className="card-head" style={{ padding: '18px 20px 14px', marginBottom: 0 }}>
          <div>
            <div className="t-section">Absenteeism risk</div>
            <div className="t-meta" style={{ marginTop: 2 }}>Employees flagged by the model, with the reason</div>
          </div>
          <Link href="/hr/alertes" className="btn-secondary" style={{ padding: '7px 13px', fontSize: '.78rem' }}>
            View all <ArrowRight size={13} />
          </Link>
        </div>

        {risk === null ? (
          <div style={{ padding: 20 }}><div className="skeleton" style={{ height: 130 }} /></div>
        ) : risk.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><AlertTriangle size={18} /></div>
            <div style={{ color: 'var(--ink-2)', fontWeight: 550 }}>No employees currently at risk</div>
            <div className="t-meta" style={{ marginTop: 3 }}>Everyone is tracking close to the company baseline.</div>
          </div>
        ) : (
          <table>
            <thead>
              <tr><th>Employee</th><th style={{ width: 110 }}>Risk</th><th style={{ width: 150 }}>Level</th><th>Main driver</th></tr>
            </thead>
            <tbody>
              {risk.slice(0, 6).map((r: any) => {
                const critical = r.niveau === 'Critique';
                const tone = critical ? RED : AMBER;
                const reason = (r.raisons && r.raisons[0]?.text) || r.explication || '—';
                return (
                  <tr key={r.employe_id}>
                    <td style={{ fontWeight: 600, color: 'var(--ink)' }}>{r.nom}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-track" style={{ width: 52 }}>
                          <div className="progress-fill" style={{ width: `${Math.min(100, r.probabilite)}%`, background: tone }} />
                        </div>
                        <span className="t-num" style={{ fontWeight: 650, color: tone }}>{r.probabilite}%</span>
                      </div>
                    </td>
                    <td><span className={critical ? 'badge badge-red' : 'badge badge-amber'}>{critical ? 'Critical' : 'Medium'}</span></td>
                    <td className="t-meta">{reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
