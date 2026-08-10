'use client';
import { useEffect, useState } from 'react';
import { TrendingDown, Clock, BarChart2, Umbrella } from 'lucide-react';

export default function Statistiques() {
  const [kpis, setKpis] = useState<any>({});
  const [evol, setEvol] = useState<any[]>([]);
  const [deps, setDeps] = useState<any[]>([]);
  const [tab,  setTab]  = useState('evolution');

  useEffect(() => {
    fetch('/api/pointages/kpis/global').then(r => r.json()).then(d => setKpis(d || {}));
    fetch('/api/pointages/stats/evolution').then(r => r.json()).then(d => setEvol(Array.isArray(d) ? d : []));
    fetch('/api/pointages/kpis/departement').then(r => r.json()).then(d => setDeps(Array.isArray(d) ? d : []));
  }, []);

  const kpiCards = [
    { label: 'Absenteeism',    value: `${(kpis.taux_absenteisme || 0).toFixed(1)}%`, color: '#f85149', dimBg: 'rgba(248,81,73,0.15)',   Icon: TrendingDown },
    { label: 'Late rate',      value: `${(kpis.taux_retard || 0).toFixed(1)}%`,       color: '#e3b341', dimBg: 'rgba(227,179,65,0.15)',  Icon: Clock },
    { label: 'Avg hours/day',  value: `${(kpis.moy_heures_jour || 0).toFixed(1)}h`,   color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)',  Icon: BarChart2 },
    { label: 'Total leave',    value: kpis.total_conges || 0,                          color: '#45B9E9', dimBg: 'rgba(11,135,190,0.15)', Icon: Umbrella },
  ];

  const tabList = [
    { key: 'evolution', label: 'Monthly Evolution' },
    { key: 'deps',      label: 'By Department' },
  ];

  function DataTable({ rows }: { rows: any[] }) {
    if (rows.length === 0) {
      return <div style={{ textAlign: 'center', padding: 40, color: '#9DB3C2' }}>No data available</div>;
    }
    const headers = Object.keys(rows[0] || {});
    return (
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'rgba(12,36,54,0.04)' }}>
              {headers.map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.66rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any, i: number) => (
              <tr key={i} style={{ transition: 'background 0.1s' }}
                onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
              >
                {Object.values(row).map((v: any, j: number) => (
                  <td key={j} style={{ padding: '11px 16px', fontSize: '0.78rem', color: '#34546A', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                    {typeof v === 'number' ? v.toFixed(1) : v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Statistics & KPIs</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>HR performance indicators</p>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
        {kpiCards.map((k, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: k.dimBg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
              <k.Icon size={17} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ fontSize: '0.68rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {tabList.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 18px', borderRadius: 10,
            border: tab === t.key ? 'none' : '1.5px solid rgba(12,36,54,0.04)',
            background: tab === t.key ? 'var(--brand-600)' : 'rgba(12,36,54,0.04)',
            color: tab === t.key ? 'white' : '#6B879B',
            fontWeight: 600, fontSize: '0.82rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif', transition: 'all 0.12s',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Table card */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>
          {tab === 'evolution' ? 'Monthly evolution' : 'KPIs by department'}
        </div>
        {tab === 'evolution' ? <DataTable rows={evol} /> : <DataTable rows={deps} />}
      </div>
    </div>
  );
}
