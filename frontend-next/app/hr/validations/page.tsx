'use client';
import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Umbrella, FileText, Plane, Calendar, Clock } from 'lucide-react';

export default function Validations() {
  const [conges,   setConges]   = useState<any[]>([]);
  const [docs,     setDocs]     = useState<any[]>([]);
  const [missions, setMissions] = useState<any[]>([]);
  const [tab,      setTab]      = useState('conges');
  const [user,     setUser]     = useState<any>(null);

  useEffect(() => {
    try { setUser(JSON.parse(localStorage.getItem('inet_user') || '{}')); } catch {}
    fetch('/api/conges/en-attente/all').then(r => r.json()).then(d => setConges(d || []));
    fetch('/api/documents/en-attente').then(r => r.json()).then(d => setDocs(d || []));
    fetch('/api/missions/en-attente').then(r => r.json()).then(d => setMissions(d || []));
  }, []);

  async function validerConge(id: number, approuve: boolean) {
    const rh_id = user?.employe?.employe_id || 1;
    await fetch(`/api/conges/valider/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rh_id, approuve, commentaire: '' }),
    });
    fetch('/api/conges/en-attente/all').then(r => r.json()).then(d => setConges(d || []));
  }

  async function validerDoc(id: number, approuve: boolean) {
    const rh_id = user?.employe?.employe_id || 1;
    await fetch(`/api/documents/${id}/valider`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rh_id, approuve, commentaire: '' }),
    });
    fetch('/api/documents/en-attente').then(r => r.json()).then(d => setDocs(d || []));
  }

  async function validerMission(id: number, approuve: boolean) {
    const rh_id = user?.employe?.employe_id || 1;
    await fetch(`/api/missions/${id}/valider`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rh_id, approuve, commentaire: '' }),
    });
    fetch('/api/missions/en-attente').then(r => r.json()).then(d => setMissions(d || []));
  }

  const tabs = [
    { key: 'conges',   label: 'Leave',     Icon: Umbrella, count: conges.length },
    { key: 'docs',     label: 'Documents', Icon: FileText, count: docs.length },
    { key: 'missions', label: 'Missions',  Icon: Plane,    count: missions.length },
  ];

  function EmptyState() {
    return (
      <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 'var(--radius-lg)', padding: 48, textAlign: 'center', border: '1px dashed rgba(255,255,255,0.1)' }}>
        <CheckCircle2 size={32} color="#3fb950" style={{ margin: '0 auto 12px', display: 'block' }} />
        <div style={{ fontWeight: 700, color: '#0C2436', marginBottom: 4 }}>All clear!</div>
        <div style={{ color: '#9DB3C2', fontSize: '0.82rem' }}>No pending requests</div>
      </div>
    );
  }

  function ActionRow({ id, title, sub, onApprove, onReject }: { id: number; title: string; sub: string; onApprove: () => void; onReject: () => void }) {
    return (
      <div style={{ background: 'var(--surface)', borderRadius: 12, padding: '16px 20px', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ width: 38, height: 38, borderRadius: 10, background: 'rgba(12,36,54,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Clock size={16} color="#9DB3C2" />
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#0C2436', fontSize: '0.88rem', marginBottom: 3 }}>
              <span style={{ color: '#9DB3C2', fontWeight: 400, marginRight: 6 }}>#{id}</span>{title}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#9DB3C2', display: 'flex', alignItems: 'center', gap: 5 }}>
              <Calendar size={11} /> {sub}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={onApprove} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'rgba(46,160,67,0.15)', color: '#3fb950', border: '1px solid rgba(46,160,67,0.3)',
            borderRadius: 8, padding: '8px 16px', fontWeight: 600, fontSize: '0.8rem',
            cursor: 'pointer', fontFamily: 'Inter, sans-serif', transition: 'background 0.12s',
          }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(46,160,67,0.25)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(46,160,67,0.15)')}
          >
            <CheckCircle2 size={14} /> Approve
          </button>
          <button onClick={onReject} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'rgba(248,81,73,0.15)', color: '#f85149', border: '1px solid rgba(248,81,73,0.3)',
            borderRadius: 8, padding: '8px 16px', fontWeight: 600, fontSize: '0.8rem',
            cursor: 'pointer', fontFamily: 'Inter, sans-serif', transition: 'background 0.12s',
          }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(248,81,73,0.25)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(248,81,73,0.15)')}
          >
            <XCircle size={14} /> Reject
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Validations</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Approve or reject pending requests</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 22 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '9px 20px', borderRadius: 10, cursor: 'pointer',
            fontWeight: 600, fontSize: '0.82rem', fontFamily: 'Inter, sans-serif',
            background: tab === t.key ? 'var(--brand-600)' : '#FFFFFF',
            color: tab === t.key ? 'white' : '#6B879B',
            border: tab === t.key ? '1px solid transparent' : '1.5px solid rgba(12,36,54,0.04)',
            boxShadow: tab === t.key ? '0 2px 8px rgba(15,163,224,0.3)' : 'none',
            transition: 'all 0.12s',
          }}>
            <t.Icon size={15} />
            {t.label}
            {t.count > 0 && (
              <span style={{
                background: tab === t.key ? 'rgba(255,255,255,0.2)' : 'rgba(248,81,73,0.2)',
                color: tab === t.key ? 'white' : '#f85149',
                borderRadius: 20, padding: '1px 8px', fontSize: '0.7rem', fontWeight: 700,
              }}>{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {tab === 'conges' && (conges.length === 0 ? <EmptyState /> : conges.map(c =>
          <ActionRow key={c.conge_id} id={c.conge_id} title={c.type_conge}
            sub={`${c.date_debut} — ${c.date_fin} · ${c.nb_jours} day(s)`}
            onApprove={() => validerConge(c.conge_id, true)}
            onReject={() => validerConge(c.conge_id, false)}
          />
        ))}
        {tab === 'docs' && (docs.length === 0 ? <EmptyState /> : docs.map(d =>
          <ActionRow key={d.document_id} id={d.document_id} title={d.type_document}
            sub={`Employee #${d.employe_id} · ${String(d.date_demande).slice(0, 10)}`}
            onApprove={() => validerDoc(d.document_id, true)}
            onReject={() => validerDoc(d.document_id, false)}
          />
        ))}
        {tab === 'missions' && (missions.length === 0 ? <EmptyState /> : missions.map(m =>
          <ActionRow key={m.mission_id} id={m.mission_id} title={m.lieu}
            sub={`${m.date_debut} — ${m.date_fin} · ${m.type_mission}`}
            onApprove={() => validerMission(m.mission_id, true)}
            onReject={() => validerMission(m.mission_id, false)}
          />
        ))}
      </div>
    </div>
  );
}
