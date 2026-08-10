'use client';
import { useEffect, useState } from 'react';
import { GraduationCap, Calendar, Plus, ArrowLeft, Rocket } from 'lucide-react';

export default function Formations() {
  const [formations, setFormations] = useState<any[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [tab,        setTab]        = useState('list');
  const [form,       setForm]       = useState({
    titre: '', date_debut: '', date_fin: '',
    organisateur: '', type_formation: '', description: '',
  });

  useEffect(() => { loadFormations(); }, []);

  function loadFormations() {
    fetch('/api/formations/')
      .then(r => r.json())
      .then(d => { setFormations(Array.isArray(d) ? d : []); setLoading(false); })
      .catch(() => setLoading(false));
  }

  async function createFormation() {
    await fetch('/api/formations/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    loadFormations();
    setTab('list');
    setForm({ titre: '', date_debut: '', date_fin: '', organisateur: '', type_formation: '', description: '' });
  }

  const today    = new Date().toISOString().slice(0, 10);
  const upcoming = formations.filter(f => f.date_debut >= today).length;
  const types    = new Set(formations.map(f => f.type_formation).filter(Boolean)).size;

  const kpis = [
    { label: 'Total',    value: formations.length, color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)',  Icon: GraduationCap },
    { label: 'Upcoming', value: upcoming,           color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)',  Icon: Calendar },
    { label: 'Types',    value: types,              color: '#45B9E9', dimBg: 'rgba(11,135,190,0.15)', Icon: GraduationCap },
  ];

  const typeColors: Record<string, { bg: string; color: string }> = {
    Technique:     { bg: 'rgba(15,163,224,0.15)',  color: '#45B9E9' },
    Managériale:   { bg: 'rgba(46,160,67,0.15)',   color: '#3fb950' },
    Réglementaire: { bg: 'rgba(248,81,73,0.15)',   color: '#f85149' },
    'Soft Skills': { bg: 'rgba(227,179,65,0.15)',  color: '#e3b341' },
    Sécurité:      { bg: 'rgba(234,88,12,0.15)',   color: '#fb923c' },
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Training Management</h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Create and manage training sessions</p>
        </div>
        <button onClick={() => setTab(tab === 'create' ? 'list' : 'create')} style={{
          display: 'flex', alignItems: 'center', gap: 7,
          background: tab === 'create' ? '#FFFFFF' : 'var(--brand-600)',
          color: tab === 'create' ? '#34546A' : 'white',
          border: tab === 'create' ? '1.5px solid rgba(12,36,54,0.04)' : 'none',
          borderRadius: 10, padding: '10px 18px',
          fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'Inter, sans-serif',
          boxShadow: tab === 'create' ? 'none' : '0 2px 8px rgba(15,163,224,0.3)',
        }}>
          {tab === 'create' ? <><ArrowLeft size={15} /> Back</> : <><Plus size={15} /> New training</>}
        </button>
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

      {/* Create Form */}
      {tab === 'create' && (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '24px', border: '1px solid var(--border)', marginBottom: 20, boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0C2436', marginBottom: 18 }}>New training session</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {[
              { label: 'Title *',      key: 'titre',        placeholder: 'e.g. Advanced Excel Training' },
              { label: 'Organizer',    key: 'organisateur', placeholder: 'e.g. CNFCPP' },
              { label: 'Start date *', key: 'date_debut',   placeholder: '', type: 'date' },
              { label: 'End date *',   key: 'date_fin',     placeholder: '', type: 'date' },
            ].map(f => (
              <div key={f.key}>
                <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{f.label}</label>
                <input type={f.type || 'text'} placeholder={f.placeholder}
                  value={(form as any)[f.key]} onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                  style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', boxSizing: 'border-box', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
              </div>
            ))}
            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Type</label>
              <select value={form.type_formation} onChange={e => setForm({ ...form, type_formation: e.target.value })}
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', background: 'rgba(12,36,54,0.04)', color: '#0C2436', fontFamily: 'Inter, sans-serif' }}>
                <option value="">Select...</option>
                {['Technique', 'Managériale', 'Réglementaire', 'Soft Skills', 'Sécurité', 'Autre'].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Description</label>
              <textarea placeholder="Objectives, content, target audience..." value={form.description}
                onChange={e => setForm({ ...form, description: e.target.value })}
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', height: 80, resize: 'vertical', boxSizing: 'border-box', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
            </div>
          </div>
          <button onClick={createFormation} style={{
            marginTop: 16, display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--brand-600)', color: 'white',
            border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif', boxShadow: 'none',
          }}>
            <Rocket size={14} /> Create training
          </button>
        </div>
      )}

      {/* List */}
      {tab === 'list' && (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>
            All training sessions ({formations.length})
          </div>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2' }}>Loading...</div>
          ) : formations.length === 0 ? (
            <div style={{ padding: 48, textAlign: 'center' }}>
              <GraduationCap size={32} color="rgba(255,255,255,0.1)" style={{ margin: '0 auto 12px', display: 'block' }} />
              <div style={{ color: '#9DB3C2', fontSize: '0.85rem' }}>No training sessions yet</div>
            </div>
          ) : (
            formations.map((f: any, i: number) => {
              const tc = typeColors[f.type_formation] || { bg: 'rgba(15,163,224,0.15)', color: '#45B9E9' };
              return (
                <div key={i} style={{ padding: '14px 20px', borderBottom: i < formations.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.1s' }}
                  onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                  onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div style={{ width: 38, height: 38, borderRadius: 9, background: 'rgba(15,163,224,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <GraduationCap size={17} color="#45B9E9" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, color: '#0C2436', fontSize: '0.88rem', marginBottom: 2 }}>{f.titre}</div>
                      <div style={{ fontSize: '0.73rem', color: '#9DB3C2', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Calendar size={11} />
                        {f.date_debut} — {f.date_fin}
                        {f.organisateur && <span> · {f.organisateur}</span>}
                      </div>
                    </div>
                  </div>
                  <span style={{ background: tc.bg, color: tc.color, padding: '3px 12px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700, flexShrink: 0 }}>
                    {f.type_formation || 'General'}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
