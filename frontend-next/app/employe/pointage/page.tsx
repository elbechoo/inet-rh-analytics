'use client';
import { useEffect, useState, useCallback } from 'react';
import { CheckCircle, Clock, XCircle, Timer } from 'lucide-react';

const STEPS = [
  { key: 'ENTREE',      label: 'Check-in',    color: '#3fb950' },
  { key: 'DEBUT_PAUSE', label: 'Start break', color: '#45B9E9' },
  { key: 'FIN_PAUSE',   label: 'End break',   color: '#45B9E9' },
  { key: 'SORTIE',      label: 'Check-out',   color: '#f85149' },
];
const STEP_LABELS = ['Check-in', 'Start break', 'End break', 'Check-out'];

export default function MonPointage() {
  const [stats,    setStats]    = useState<any>({});
  const [hist,     setHist]     = useState<any[]>([]);
  const [logs,     setLogs]     = useState<any[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [pointing, setPointing] = useState(false);
  const [msg,      setMsg]      = useState<{ text: string; ok: boolean } | null>(null);
  const [userId,   setUserId]   = useState<number | null>(null);

  const fetchData = useCallback(async (id: number) => {
    const [s, h, l] = await Promise.all([
      fetch(`/api/pointages/stats/${id}`).then(r => r.json()),
      fetch(`/api/pointages/historique/${id}?limit=30`).then(r => r.json()),
      fetch(`/api/pointages/logs/today/${id}`).then(r => r.json()),
    ]);
    setStats(s || {});
    setHist(Array.isArray(h) ? h : []);
    setLogs(Array.isArray(l) ? l : []);
    setLoading(false);
  }, []);

  useEffect(() => {
    const u = JSON.parse(localStorage.getItem('inet_user') || '{}');
    const id = u?.employe?.employe_id;
    if (!id) return;
    setUserId(id);
    fetchData(id);
  }, [fetchData]);

  const currentStep = logs.length >= 4 ? 4 : logs.length;
  const isDone = currentStep >= 4;

  async function pointer() {
    if (!userId || isDone) return;
    setPointing(true);
    setMsg(null);
    const res = await fetch('/api/pointages/pointer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ employe_id: userId }),
    });
    const data = await res.json();
    if (res.ok) {
      const heure = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      setMsg({ text: `${STEP_LABELS[currentStep]} recorded at ${heure}`, ok: true });
      fetchData(userId);
    } else {
      setMsg({ text: data.detail || 'An error occurred', ok: false });
    }
    setPointing(false);
  }

  const statutStyle: Record<string, any> = {
    'Présent':          { bg: 'rgba(46,160,67,0.2)',   color: '#3fb950' },
    'En retard':        { bg: 'rgba(227,179,65,0.2)',  color: '#e3b341' },
    'Sortie manquante': { bg: 'rgba(249,115,22,0.2)',  color: '#fb923c' },
    'Absent':           { bg: 'rgba(248,81,73,0.2)',   color: '#f85149' },
  };

  const btnConfig = isDone ? { label: 'Day complete', color: '#9DB3C2' } : STEPS[currentStep];

  const kpis = [
    { label: 'Present', value: stats.nb_presents  ?? 0, color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)',   Icon: CheckCircle },
    { label: 'Late',    value: stats.nb_retards   ?? 0, color: '#e3b341', dimBg: 'rgba(227,179,65,0.15)',  Icon: Clock },
    { label: 'Absent',  value: stats.nb_absences  ?? 0, color: '#f85149', dimBg: 'rgba(248,81,73,0.15)',   Icon: XCircle },
    { label: 'Hours',   value: `${(stats.total_heures ?? 0).toFixed(0)}h`, color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)', Icon: Timer },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>My Attendance</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {/* Clock-in card */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 28, border: '1px solid var(--border)', marginBottom: 20, textAlign: 'center', boxShadow: 'var(--shadow-sm)' }}>

        {/* Timeline */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 0, marginBottom: 28, maxWidth: 480, margin: '0 auto 28px' }}>
          {STEP_LABELS.map((label, i) => {
            const done   = i < currentStep;
            const active = i === currentStep;
            const log    = logs[i];
            return (
              <div key={i} style={{ flex: 1, textAlign: 'center', position: 'relative' }}>
                {i > 0 && (
                  <div style={{
                    position: 'absolute', top: 14, left: '-50%', width: '100%', height: 2,
                    background: done ? '#3fb950' : 'rgba(255,255,255,0.1)', zIndex: 0,
                  }} />
                )}
                <div style={{
                  width: 30, height: 30, borderRadius: '50%', margin: '0 auto 6px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, position: 'relative', zIndex: 1,
                  background: done ? '#3fb950' : active ? '#0FA3E0' : 'rgba(12,36,54,0.04)',
                  color: (done || active) ? 'white' : '#9DB3C2',
                  border: `2px solid ${done ? '#3fb950' : active ? '#0FA3E0' : 'rgba(255,255,255,0.1)'}`,
                  boxShadow: active ? '0 0 0 4px rgba(15,163,224,0.2)' : 'none',
                }}>
                  {done ? <CheckCircle size={14} /> : i + 1}
                </div>
                <div style={{ fontSize: '0.65rem', color: '#9DB3C2', fontWeight: 500 }}>{label}</div>
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#0C2436', marginTop: 2 }}>
                  {log ? log.heure?.slice(0, 5) : '—'}
                </div>
              </div>
            );
          })}
        </div>

        <button onClick={pointer} disabled={pointing || isDone} style={{
          background: isDone ? 'rgba(12,36,54,0.04)' : pointing ? 'rgba(15,163,224,0.5)' : `linear-gradient(135deg,${btnConfig.color},${btnConfig.color}dd)`,
          color: isDone ? '#9DB3C2' : 'white', border: 'none', borderRadius: 12,
          padding: '14px 48px', fontWeight: 700, fontSize: '1rem',
          cursor: (pointing || isDone) ? 'not-allowed' : 'pointer',
          minWidth: 220, transition: 'all 0.15s',
          boxShadow: isDone ? 'none' : `0 4px 16px ${btnConfig.color}40`,
        }}>
          {pointing ? 'Recording...' : isDone ? 'Day complete' : btnConfig.label}
        </button>
        {msg && (
          <div style={{ marginTop: 14, fontSize: '0.84rem', color: msg.ok ? '#3fb950' : '#f85149', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            {msg.ok ? <CheckCircle size={14} /> : <XCircle size={14} />} {msg.text}
          </div>
        )}
      </div>

      {/* Stats */}
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

      {/* History table */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>
          Attendance history ({hist.length})
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2' }}>Loading...</div>
        ) : hist.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2' }}>No records yet</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(12,36,54,0.04)' }}>
                {['Date', 'Check-in', 'Brk start', 'Brk end', 'Check-out', 'Duration', 'Status'].map(h => (
                  <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontSize: '0.64rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {hist.map((p: any, i: number) => {
                const s = statutStyle[p.statut] || { bg: 'rgba(12,36,54,0.04)', color: '#6B879B' };
                return (
                  <tr key={i} style={{ transition: 'background 0.1s' }}
                    onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                    onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', fontWeight: 600, color: '#0C2436', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.date_pointage}</td>
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_entree || '—'}</td>
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', color: '#6B879B', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_debut_pause || '—'}</td>
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', color: '#6B879B', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_fin_pause || '—'}</td>
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.heure_sortie || '—'}</td>
                    <td style={{ padding: '9px 14px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{p.duree_travail ? `${p.duree_travail}h` : '—'}</td>
                    <td style={{ padding: '9px 14px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
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
