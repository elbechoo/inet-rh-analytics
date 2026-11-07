'use client';
import { useEffect, useState } from 'react';
import { AlertTriangle, Info, Zap, CheckCircle2, BookOpen, RefreshCw } from 'lucide-react';
import RiskPanel from '../../components/RiskPanel';

export default function AlertesIA() {
  const [alertes,    setAlertes]    = useState<any[]>([]);
  const [filter,     setFilter]     = useState('All');
  const [loading,    setLoading]    = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => { loadAlertes(); }, []);

  function loadAlertes() {
    fetch('/api/ai/alertes?limit=100')
      .then(r => r.json())
      .then(d => { setAlertes(d || []); setLoading(false); });
  }

  async function generer() {
    setGenerating(true);
    await fetch('/api/ai/generer-alertes', { method: 'POST' });
    loadAlertes();
    setGenerating(false);
  }

  async function marquerLue(id: number) {
    await fetch(`/api/ai/alertes/${id}/lue`, { method: 'PUT' });
    setAlertes(prev => prev.map(a => a.alerte_id === id ? { ...a, est_lue: true } : a));
  }

  async function marquerToutesLues() {
    const ids = alertes.filter(a => !a.est_lue).map(a => a.alerte_id);
    await Promise.all(ids.map(id => fetch(`/api/ai/alertes/${id}/lue`, { method: 'PUT' })));
    setAlertes(prev => prev.map(a => ({ ...a, est_lue: true })));
  }

  const FILTERS = ['All', 'Critique', 'Moyen', 'Info'];
  const filtered  = filter === 'All' ? alertes : alertes.filter(a => a.niveau === filter);
  const critiques = alertes.filter(a => a.niveau === 'Critique').length;
  const moyens    = alertes.filter(a => a.niveau === 'Moyen').length;
  const infos     = alertes.filter(a => a.niveau === 'Info').length;
  const nonLues   = alertes.filter(a => !a.est_lue).length;

  const nivCfg: Record<string, { bar: string; badge: string; text: string; Icon: React.ElementType }> = {
    Critique: { bar: '#f85149', badge: 'rgba(248,81,73,0.15)',   text: '#f85149', Icon: AlertTriangle },
    Moyen:    { bar: '#e3b341', badge: 'rgba(227,179,65,0.15)',  text: '#e3b341', Icon: AlertTriangle },
    Info:     { bar: '#45B9E9', badge: 'rgba(15,163,224,0.15)',  text: '#45B9E9', Icon: Info },
  };

  const kpis = [
    { label: 'Critical', value: critiques, color: '#f85149', dimBg: 'rgba(248,81,73,0.15)' },
    { label: 'Medium',   value: moyens,    color: '#e3b341', dimBg: 'rgba(227,179,65,0.15)' },
    { label: 'Info',     value: infos,     color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)' },
    { label: 'Unread',   value: nonLues,   color: '#45B9E9', dimBg: 'rgba(11,135,190,0.15)' },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>AI Alerts</h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Anomalies and absenteeism predictions</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {nonLues > 0 && (
            <button onClick={marquerToutesLues} style={{
              display: 'flex', alignItems: 'center', gap: 7,
              background: 'var(--surface)', color: '#0C2436', border: '1px solid var(--border)',
              borderRadius: 10, padding: '9px 16px', fontWeight: 600, fontSize: '0.82rem',
              cursor: 'pointer', fontFamily: 'Inter, sans-serif', transition: 'background 0.12s',
            }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = '#FFFFFF')}
            >
              <CheckCircle2 size={15} color="#3fb950" /> Mark all as read ({nonLues})
            </button>
          )}
          <button onClick={generer} disabled={generating} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: generating ? 'rgba(15,163,224,0.4)' : 'var(--brand-600)',
            color: 'white', border: 'none', borderRadius: 10, padding: '9px 18px',
            fontWeight: 600, fontSize: '0.82rem', cursor: generating ? 'not-allowed' : 'pointer',
            fontFamily: 'Inter, sans-serif', transition: 'opacity 0.15s',
            boxShadow: generating ? 'none' : '0 2px 8px rgba(15,163,224,0.3)',
          }}>
            {generating
              ? <><RefreshCw size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating...</>
              : <><Zap size={14} /> Generate alerts</>
            }
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 22 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: k.dimBg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
              <AlertTriangle size={17} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{ fontSize: '0.68rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Explainable AI - at-risk employees with reasons */}
      <RiskPanel />

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '7px 18px', borderRadius: 8,
            border: filter === f ? 'none' : '1.5px solid rgba(12,36,54,0.04)',
            background: filter === f ? 'var(--brand-600)' : 'rgba(12,36,54,0.04)',
            color: filter === f ? 'white' : '#6B879B',
            fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif', transition: 'all 0.12s',
          }}>{f}</button>
        ))}
      </div>

      {/* Alerts list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9DB3C2' }}>Loading...</div>
      ) : filtered.length === 0 ? (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 48, textAlign: 'center', border: '1px solid var(--border)' }}>
          <BookOpen size={32} color="rgba(255,255,255,0.1)" style={{ margin: '0 auto 12px', display: 'block' }} />
          <div style={{ fontWeight: 700, color: '#0C2436', marginBottom: 6 }}>No alerts</div>
          <div style={{ color: '#9DB3C2', fontSize: '0.82rem' }}>Click "Generate alerts" to run the AI analysis</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((a: any) => {
            const c = nivCfg[a.niveau] || nivCfg.Info;
            return (
              <div key={a.alerte_id} style={{
                background: 'var(--surface)', borderRadius: 12,
                border: '1px solid var(--border)',
                borderLeft: `4px solid ${c.bar}`,
                padding: '14px 18px', display: 'flex',
                justifyContent: 'space-between', alignItems: 'center',
                opacity: a.est_lue ? 0.5 : 1, transition: 'opacity 0.15s',
                boxShadow: a.est_lue ? 'none' : '0 1px 3px rgba(0,0,0,0.3)',
              }}>
                <div style={{ flex: 1, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: c.badge, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                    <c.Icon size={15} style={{ color: c.text }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                      <span style={{ background: c.badge, color: c.text, fontSize: '0.62rem', fontWeight: 700, padding: '2px 8px', borderRadius: 20, letterSpacing: '0.3px' }}>{a.niveau}</span>
                      <span style={{ fontSize: '0.70rem', color: '#9DB3C2' }}>{String(a.date_alerte).slice(0, 16)}</span>
                      {a.est_lue && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.65rem', color: '#3fb950', fontWeight: 600 }}>
                          <CheckCircle2 size={11} /> Read
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 500, color: '#34546A', lineHeight: 1.4 }}>{a.message}</div>
                  </div>
                </div>
                {!a.est_lue && (
                  <button onClick={() => marquerLue(a.alerte_id)} style={{
                    background: 'rgba(12,36,54,0.04)', border: '1px solid var(--border)', borderRadius: 8,
                    padding: '7px 14px', fontSize: '0.75rem', fontWeight: 600, color: '#34546A',
                    cursor: 'pointer', marginLeft: 14, flexShrink: 0, fontFamily: 'Inter, sans-serif',
                    transition: 'background 0.12s',
                  }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                  >
                    Mark as read
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
