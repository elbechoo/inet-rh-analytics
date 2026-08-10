'use client';
import { useEffect, useState } from 'react';
import { Calendar, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export default function Absences() {
  const [absences,  setAbsences]  = useState<any[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [dateDebut, setDateDebut] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  });
  const [dateFin, setDateFin] = useState(() => new Date().toISOString().slice(0, 10));

  useEffect(() => { load(); }, [dateDebut, dateFin]);

  function load() {
    setLoading(true);
    fetch('/api/employes/absences/all')
      .then(r => r.json())
      .then(d => { setAbsences(Array.isArray(d) ? d : []); setLoading(false); })
      .catch(() => setLoading(false));
  }

  const justifiees    = absences.filter(a => a.justifiee).length;
  const nonJustifiees = absences.filter(a => !a.justifiee).length;

  const kpis = [
    { label: 'Total absences', value: absences.length, color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)',  Icon: Calendar },
    { label: 'Justified',      value: justifiees,      color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)',   Icon: CheckCircle2 },
    { label: 'Unjustified',    value: nonJustifiees,   color: '#f85149', dimBg: 'rgba(248,81,73,0.15)',  Icon: XCircle },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Absences</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Track and analyze employee absences</p>
      </div>

      {/* KPIs */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: k.dimBg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
              <k.Icon size={17} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ fontSize: '0.68rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ background: 'var(--surface)', borderRadius: 12, padding: '16px 20px', border: '1px solid var(--border)', marginBottom: 16, display: 'flex', gap: 20, alignItems: 'flex-end' }}>
        <div>
          <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Start date</label>
          <input type="date" value={dateDebut} onChange={e => setDateDebut(e.target.value)}
            style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem', outline: 'none', fontFamily: 'Inter, sans-serif', width: 'auto', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
        </div>
        <div>
          <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>End date</label>
          <input type="date" value={dateFin} onChange={e => setDateFin(e.target.value)}
            style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', fontSize: '0.82rem', outline: 'none', fontFamily: 'Inter, sans-serif', width: 'auto', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Absences ({absences.length})</span>
          {loading && <span style={{ fontSize: '0.72rem', color: '#9DB3C2' }}>Loading...</span>}
        </div>
        {!loading && absences.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <AlertCircle size={32} color="rgba(255,255,255,0.1)" style={{ margin: '0 auto 12px', display: 'block' }} />
            <div style={{ color: '#9DB3C2', fontSize: '0.85rem' }}>No absences found for this period</div>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(12,36,54,0.04)' }}>
                {/* "Status" column dropped — it duplicated "Justified" (Justifiée / Non justifiée). */}
                {['Employee', 'Date', 'Reason', 'Justified'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.66rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {absences.map((a: any, i: number) => (
                <tr key={i} style={{ transition: 'background 0.1s' }}
                  onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                  onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '12px 16px', fontSize: '0.82rem', fontWeight: 600, color: '#0C2436', borderTop: '1px solid rgba(12,36,54,0.04)' }}>#{a.employe_id}</td>
                  <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#6B879B', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{a.date_absence}</td>
                  <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{a.motif || '—'}</td>
                  <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                    <span style={{
                      background: a.justifiee ? 'rgba(46,160,67,0.2)'  : 'rgba(248,81,73,0.2)',
                      color:      a.justifiee ? '#3fb950'              : '#f85149',
                      padding: '3px 10px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700,
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                    }}>
                      {a.justifiee ? 'Yes' : 'No'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
