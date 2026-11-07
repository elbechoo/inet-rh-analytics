'use client';
import { useEffect, useState } from 'react';
import { GraduationCap, Calendar, CheckCircle2 } from 'lucide-react';

export default function MesFormationsPage() {
  const [formations, setFormations] = useState<any[]>([]);
  const [loading,    setLoading]    = useState(true);

  useEffect(() => {
    fetch('/api/formations/')
      .then(r => r.json())
      .then(d => { setFormations(Array.isArray(d) ? d : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const today    = new Date().toISOString().slice(0, 10);
  const upcoming = formations.filter(f => f.date_debut >= today);
  const past     = formations.filter(f => f.date_debut < today);

  const kpis = [
    { label: 'Total',    value: formations.length, color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)',  Icon: GraduationCap },
    { label: 'Upcoming', value: upcoming.length,   color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)',  Icon: Calendar },
    { label: 'Past',     value: past.length,        color: '#45B9E9', dimBg: 'rgba(11,135,190,0.15)', Icon: CheckCircle2 },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>

      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>My Training</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Available sessions and history</p>
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

      {/* Upcoming */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', marginBottom: 16, overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Calendar size={14} color="#3fb950" /> Upcoming ({upcoming.length})
        </div>
        {loading ? (
          <div style={{ padding: 30, textAlign: 'center', color: '#9DB3C2' }}>Loading...</div>
        ) : upcoming.length === 0 ? (
          <div style={{ padding: 30, textAlign: 'center', color: '#9DB3C2', fontSize: '0.82rem' }}>No upcoming training sessions</div>
        ) : upcoming.map((f: any, i: number) => (
          <div key={i} style={{ padding: '14px 20px', borderBottom: i < upcoming.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.1s' }}
            onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
            onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(15,163,224,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <GraduationCap size={16} color="#45B9E9" />
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#0C2436', fontSize: '0.88rem', marginBottom: 2 }}>{f.titre}</div>
                <div style={{ fontSize: '0.73rem', color: '#9DB3C2', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Calendar size={11} />
                  {f.date_debut} - {f.date_fin}
                  {f.organisateur && <span> · {f.organisateur}</span>}
                </div>
              </div>
            </div>
            <span style={{ background: 'rgba(15,163,224,0.15)', color: '#45B9E9', padding: '3px 10px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700, flexShrink: 0 }}>
              {f.type_formation || 'General'}
            </span>
          </div>
        ))}
      </div>

      {/* Past */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)', opacity: past.length === 0 ? 1 : 0.85 }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle2 size={14} color="#45B9E9" /> Past sessions ({past.length})
        </div>
        {past.length === 0 ? (
          <div style={{ padding: 30, textAlign: 'center', color: '#9DB3C2', fontSize: '0.82rem' }}>No past training sessions</div>
        ) : past.map((f: any, i: number) => (
          <div key={i} style={{ padding: '14px 20px', borderBottom: i < past.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.1s' }}
            onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
            onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ width: 36, height: 36, borderRadius: 9, background: 'rgba(12,36,54,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <GraduationCap size={16} color="#9DB3C2" />
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#6B879B', fontSize: '0.88rem', marginBottom: 2 }}>{f.titre}</div>
                <div style={{ fontSize: '0.73rem', color: '#9DB3C2', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Calendar size={11} />
                  {f.date_debut} - {f.date_fin}
                </div>
              </div>
            </div>
            <span style={{ background: 'rgba(12,36,54,0.04)', color: '#9DB3C2', padding: '3px 10px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700, flexShrink: 0 }}>
              Completed
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
