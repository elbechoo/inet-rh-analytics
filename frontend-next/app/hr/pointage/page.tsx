'use client';
import { useEffect, useState } from 'react';
import { UserCheck, Clock, AlertTriangle, XCircle, TrendingUp } from 'lucide-react';

export default function GestionPointage() {
  const [pointages, setPointages] = useState<any[]>([]);
  const [employes,  setEmployes]  = useState<any[]>([]);
  const [filter,    setFilter]    = useState('All');
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/pointages/today').then(r => r.json()),
      fetch('/api/employes/').then(r => r.json()),
    ]).then(([p, e]) => {
      setPointages(p || []);
      setEmployes(e || []);
      setLoading(false);
    });
  }, []);

  const tot = employes.length;
  const pr  = pointages.filter((p: any) => ['Présent', 'Present'].includes(p.statut)).length;
  const re  = pointages.filter((p: any) => p.statut === 'En retard').length;
  const sm  = pointages.filter((p: any) => p.statut === 'Sortie manquante').length;
  const ab  = Math.max(0, tot - pr - re - sm);
  const tx  = tot ? Math.round(pr / tot * 100) : 0;

  const FILTER_MAP: Record<string, string> = {
    'All': 'All', 'Present': 'Présent', 'Late': 'En retard', 'Missing exit': 'Sortie manquante',
  };

  const filtered = filter === 'All'
    ? pointages
    : pointages.filter((p: any) => p.statut === FILTER_MAP[filter] || p.statut === filter);

  const statutStyle: Record<string, any> = {
    'Présent':          { bg: 'rgba(46,160,67,0.2)',   color: '#3fb950' },
    'Present':          { bg: 'rgba(46,160,67,0.2)',   color: '#3fb950' },
    'En retard':        { bg: 'rgba(227,179,65,0.2)',  color: '#e3b341' },
    'Sortie manquante': { bg: 'rgba(249,115,22,0.2)',  color: '#fb923c' },
    'Absent':           { bg: 'rgba(248,81,73,0.2)',   color: '#f85149' },
  };

  const kpis = [
    { label: 'Present',      value: pr,       color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)',   Icon: UserCheck },
    { label: 'Late',         value: re,       color: '#e3b341', dimBg: 'rgba(227,179,65,0.15)',  Icon: Clock },
    { label: 'Missing exit', value: sm,       color: '#fb923c', dimBg: 'rgba(249,115,22,0.15)',  Icon: AlertTriangle },
    { label: 'Absent',       value: ab,       color: '#f85149', dimBg: 'rgba(248,81,73,0.15)',   Icon: XCircle },
    { label: 'Rate',         value: `${tx}%`, color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)',  Icon: TrendingUp },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Attendance</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>
          Real-time - {new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {/* KPIs */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '16px 18px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ width: 34, height: 34, borderRadius: 9, background: k.dimBg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
              <k.Icon size={16} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ fontSize: '0.65rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Attendance bar */}
      <div style={{ background: 'var(--surface)', borderRadius: 12, padding: '16px 20px', border: '1px solid var(--border)', marginBottom: 16, boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: '0.78rem', color: '#6B879B', fontWeight: 500 }}>Attendance rate today</span>
          <span style={{ fontWeight: 700, color: tx > 80 ? '#3fb950' : '#e3b341', fontSize: '0.82rem' }}>{tx}%</span>
        </div>
        <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 99, height: 8, overflow: 'hidden' }}>
          <div style={{ background: tx > 80 ? 'linear-gradient(90deg,#3fb950,#2ea043)' : 'linear-gradient(90deg,#e3b341,#d99f30)', width: `${tx}%`, height: 8, borderRadius: 99, transition: 'width 0.8s ease' }} />
        </div>
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['All', 'Present', 'Late', 'Missing exit'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '6px 14px', borderRadius: 8,
            border: filter === f ? 'none' : '1.5px solid rgba(12,36,54,0.04)',
            background: filter === f ? 'var(--brand-600)' : 'rgba(12,36,54,0.04)',
            color: filter === f ? 'white' : '#6B879B',
            fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif', transition: 'all 0.12s',
          }}>{f}</button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2' }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2' }}>No attendance records today</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(12,36,54,0.04)' }}>
                {['Employee', 'Check-in', 'Check-out', 'Duration', 'Late (min)', 'Status'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.66rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((p: any, i: number) => {
                const s = statutStyle[p.statut] || { bg: 'rgba(12,36,54,0.04)', color: '#6B879B' };
                return (
                  <tr key={i} style={{ transition: 'background 0.1s' }}
                    onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                    onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '0.82rem', fontWeight: 600, color: '#0C2436', borderTop: '1px solid rgba(12,36,54,0.04)' }}>#{p.employe_id}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_entree || '-'}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_sortie || '-'}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.duree_travail ? `${p.duree_travail}h` : '-'}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: p.retard_minutes > 0 ? '#e3b341' : '#3fb950', fontWeight: 600, borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.retard_minutes || 0}</td>
                    <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                      <span style={{ background: s.bg, color: s.color, padding: '3px 10px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700 }}>{p.statut}</span>
                    </td>
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
