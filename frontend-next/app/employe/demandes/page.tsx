'use client';
import { useEffect, useState } from 'react';
import { Plus, ArrowLeft, Send } from 'lucide-react';

export default function MesDemandesEmploye() {
  const [conges, setConges] = useState<any[]>([]);
  const [solde,  setSolde]  = useState<any>({});
  const [tab,    setTab]    = useState('list');
  const [user,   setUser]   = useState<any>(null);
  const [form,   setForm]   = useState({ type_conge: 'Annuel', date_debut: '', date_fin: '', commentaire: '' });
  const [msg,    setMsg]    = useState<{ text: string; ok: boolean } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem('inet_user') || '{}');
      setUser(u);
      loadData(u);
    } catch {}
  }, []);

  function loadData(u: any) {
    const id = u?.employe?.employe_id;
    if (!id) return;
    fetch(`/api/conges/${id}`).then(r => r.json()).then(d => setConges(Array.isArray(d) ? d : []));
    fetch(`/api/conges/solde/${id}`).then(r => r.json()).then(d => setSolde(d || {}));
  }

  async function soumettre() {
    const id = user?.employe?.employe_id;
    if (!form.date_debut || !form.date_fin) { setMsg({ text: 'Start and end dates are required', ok: false }); return; }
    setSubmitting(true);
    const res = await fetch(`/api/conges/demande/${id}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setMsg({ text: 'Request submitted successfully', ok: true });
      loadData(user);
      setTab('list');
      setForm({ type_conge: 'Annuel', date_debut: '', date_fin: '', commentaire: '' });
    } else {
      const d = await res.json();
      setMsg({ text: d.detail || 'An error occurred', ok: false });
    }
    setSubmitting(false);
  }

  const statutColor: Record<string, string> = { 'Approuvé': '#3fb950', 'En attente': '#e3b341', 'Refusé': '#f85149' };
  const statutBg: Record<string, string>    = { 'Approuvé': 'rgba(46,160,67,0.2)', 'En attente': 'rgba(227,179,65,0.2)', 'Refusé': 'rgba(248,81,73,0.2)' };
  const statutLabel: Record<string, string> = { 'Approuvé': 'Approved', 'En attente': 'Pending', 'Refusé': 'Rejected' };

  const sr  = solde.solde_restant ?? 0;
  const sa  = solde.solde_annuel ?? 30;
  const pct = sa ? Math.round((solde.solde_utilise ?? 0) / sa * 100) : 0;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>My Requests</h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Leave requests and balances</p>
        </div>
        <button onClick={() => { setTab(tab === 'create' ? 'list' : 'create'); setMsg(null); }} style={{
          display: 'flex', alignItems: 'center', gap: 7,
          background: tab === 'create' ? '#FFFFFF' : 'var(--brand-600)',
          color: tab === 'create' ? '#34546A' : 'white',
          border: tab === 'create' ? '1.5px solid rgba(12,36,54,0.04)' : 'none',
          borderRadius: 10, padding: '10px 18px', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
          fontFamily: 'Inter, sans-serif',
          boxShadow: tab === 'create' ? 'none' : '0 2px 8px rgba(15,163,224,0.3)',
        }}>
          {tab === 'create' ? <><ArrowLeft size={15} /> Back</> : <><Plus size={15} /> New request</>}
        </button>
      </div>

      {/* Leave balance card */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 24px', border: '1px solid var(--border)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 40, boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: '#45B9E9', lineHeight: 1 }}>{sr}</div>
          <div style={{ fontSize: '0.65rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>Days remaining</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: '0.78rem', color: '#6B879B' }}>Leave used</span>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#0C2436' }}>{solde.solde_utilise ?? 0} / {sa} days</span>
          </div>
          <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 99, height: 7, overflow: 'hidden' }}>
            <div style={{ background: 'linear-gradient(90deg,#0FA3E0,#0B87BE)', width: `${pct}%`, height: 7, borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
        </div>
      </div>

      {/* Create Form */}
      {tab === 'create' && (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '24px', border: '1px solid var(--border)', marginBottom: 20, boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0C2436', marginBottom: 18 }}>New leave request</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Leave type</label>
              <select value={form.type_conge} onChange={e => setForm({ ...form, type_conge: e.target.value })}
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', background: 'rgba(12,36,54,0.04)', color: '#0C2436', fontFamily: 'Inter, sans-serif' }}>
                {['Annuel', 'Maladie', 'Maternité', 'Familial', 'Sans solde'].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Start date</label>
              <input type="date" value={form.date_debut} onChange={e => setForm({ ...form, date_debut: e.target.value })}
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', boxSizing: 'border-box', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
            </div>
            <div>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>End date</label>
              <input type="date" value={form.date_fin} onChange={e => setForm({ ...form, date_fin: e.target.value })}
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', boxSizing: 'border-box', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reason (optional)</label>
              <textarea value={form.commentaire} onChange={e => setForm({ ...form, commentaire: e.target.value })}
                placeholder="Add a comment..."
                style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px', fontSize: '0.84rem', outline: 'none', height: 80, resize: 'vertical', boxSizing: 'border-box', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }} />
            </div>
          </div>
          {msg && (
            <div style={{ marginTop: 12, fontSize: '0.82rem', color: msg.ok ? '#3fb950' : '#f85149', background: msg.ok ? 'rgba(46,160,67,0.15)' : 'rgba(248,81,73,0.15)', border: `1px solid ${msg.ok ? 'rgba(46,160,67,0.3)' : 'rgba(248,81,73,0.3)'}`, padding: '8px 12px', borderRadius: 8 }}>
              {msg.text}
            </div>
          )}
          <button onClick={soumettre} disabled={submitting} style={{
            marginTop: 16, display: 'flex', alignItems: 'center', gap: 7,
            background: submitting ? 'rgba(15,163,224,0.4)' : 'var(--brand-600)', color: 'white',
            border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 600, fontSize: '0.85rem',
            cursor: submitting ? 'not-allowed' : 'pointer', fontFamily: 'Inter, sans-serif',
            boxShadow: submitting ? 'none' : '0 2px 8px rgba(15,163,224,0.3)',
          }}>
            <Send size={14} /> {submitting ? 'Submitting...' : 'Submit request'}
          </button>
        </div>
      )}

      {/* List */}
      {tab === 'list' && (
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>My leave requests</span>
            <span style={{ fontSize: '0.72rem', color: '#6B879B', background: 'rgba(12,36,54,0.04)', padding: '3px 10px', borderRadius: 20 }}>{conges.length} total</span>
          </div>
          {conges.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2', fontSize: '0.85rem' }}>No requests yet</div>
          ) : conges.map((c: any, i: number) => (
            <div key={i} style={{ padding: '14px 20px', borderBottom: i < conges.length - 1 ? '1px solid rgba(12,36,54,0.04)' : 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'background 0.1s' }}
              onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
              onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
            >
              <div>
                <div style={{ fontWeight: 600, color: '#0C2436', fontSize: '0.88rem', marginBottom: 3 }}>
                  <span style={{ color: '#9DB3C2', fontWeight: 400, marginRight: 6 }}>#{c.conge_id}</span>{c.type_conge}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#9DB3C2' }}>{c.date_debut} - {c.date_fin} · {c.nb_jours} day(s)</div>
              </div>
              <span style={{ background: statutBg[c.statut] || 'rgba(12,36,54,0.04)', color: statutColor[c.statut] || '#6B879B', padding: '3px 12px', borderRadius: 20, fontSize: '0.70rem', fontWeight: 700 }}>
                {statutLabel[c.statut] || c.statut}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
