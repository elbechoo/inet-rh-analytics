'use client';
import { useEffect, useState } from 'react';
import { ShieldCheck, Filter, RefreshCw, User, Clock, Info } from 'lucide-react';

type Entry = {
  audit_id: number;
  date_action: string | null;
  username: string | null;
  role: string | null;
  action: string;
  entite: string | null;
  entite_id: number | null;
  cible_employe_id: number | null;
  ancienne_valeur: string | null;
  nouvelle_valeur: string | null;
  detail: string | null;
  adresse_ip: string | null;
};

// Readable labels, and a severity so the eye lands on the consequential ones.
const ACTIONS: Record<string, { label: string; tone: 'red' | 'amber' | 'blue' | 'green' }> = {
  'conge.valider':               { label: 'Leave approved',   tone: 'green' },
  'conge.refuser':               { label: 'Leave rejected',   tone: 'amber' },
  'conge.annuler':               { label: 'Leave cancelled',  tone: 'blue'  },
  'employe.creer':               { label: 'Employee created', tone: 'blue'  },
  'employe.modifier':            { label: 'Employee updated', tone: 'blue'  },
  'employe.supprimer':           { label: 'Employee removed', tone: 'red'   },
  'utilisateur.role':            { label: 'Role changed',     tone: 'red'   },
  'utilisateur.statut':          { label: 'Account status',   tone: 'amber' },
  'utilisateur.reset_password':  { label: 'Password reset',   tone: 'red'   },
  'document.valider':            { label: 'Document validated', tone: 'blue' },
  'jour_ferie.modifier':         { label: 'Holiday changed',  tone: 'blue'  },
  'import.commit':               { label: 'Data imported',    tone: 'amber' },
};

const TONE: Record<string, { bg: string; color: string }> = {
  red:   { bg: 'rgba(220,38,38,0.10)',  color: '#B91C1C' },
  amber: { bg: 'rgba(245,158,11,0.13)', color: '#B45309' },
  blue:  { bg: 'rgba(15,163,224,0.12)', color: '#0B87BE' },
  green: { bg: 'rgba(18,165,148,0.12)', color: '#0E8C7E' },
};

export default function AuditPage() {
  const [rows, setRows]       = useState<Entry[]>([]);
  const [actions, setActions] = useState<{ action: string; count: number }[]>([]);
  const [filter, setFilter]   = useState('');
  const [days, setDays]       = useState(90);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, [filter, days]);

  async function load() {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ jours: String(days), limit: '300' });
      if (filter) qs.set('action', filter);
      const [r, a] = await Promise.all([
        fetch(`/api/admin/audit?${qs}`, { credentials: 'include' }).then(x => x.json()),
        fetch('/api/admin/audit/actions', { credentials: 'include' }).then(x => x.json()),
      ]);
      setRows(Array.isArray(r) ? r : []);
      setActions(Array.isArray(a) ? a : []);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px',
    fontSize: '0.82rem', outline: 'none', fontFamily: 'Inter, sans-serif',
    background: 'rgba(12,36,54,0.04)', color: '#0C2436', cursor: 'pointer',
  };

  return (
    <div className="view-enter" style={{ maxWidth: 1200, margin: '0 auto' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>
            Audit Trail
          </h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>
            Who changed what, and when
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select value={filter} onChange={e => setFilter(e.target.value)} style={inputStyle}>
            <option value="">All actions</option>
            {actions.map(a => (
              <option key={a.action} value={a.action}>
                {(ACTIONS[a.action]?.label ?? a.action)} ({a.count})
              </option>
            ))}
          </select>
          <select value={days} onChange={e => setDays(Number(e.target.value))} style={inputStyle}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <button onClick={load} style={{ ...inputStyle, display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 18,
        background: 'rgba(15,163,224,0.06)', border: '1px solid rgba(15,163,224,0.18)',
        borderRadius: 10, padding: '12px 14px', fontSize: '0.78rem',
        color: '#34546A', lineHeight: 1.6,
      }}>
        <Info size={15} style={{ color: '#0B87BE', flexShrink: 0, marginTop: 1 }} />
        <span>
          A permanent record of decisions affecting employment — approvals, role changes,
          deletions. Entries are never edited or removed. For technical diagnostics see
          System&nbsp;Logs, which rotate and are eventually discarded.
        </span>
      </div>

      {loading && <div style={{ color: '#6B879B', fontSize: '0.84rem', padding: 20 }}>Loading…</div>}

      {!loading && rows.length === 0 && (
        <div style={{
          background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '48px 24px',
          border: '1px solid var(--border)', textAlign: 'center', boxShadow: 'var(--shadow-sm)',
        }}>
          <ShieldCheck size={26} style={{ color: '#9DB3C2', marginBottom: 12 }} />
          <div style={{ fontWeight: 600, color: '#34546A', fontSize: '0.9rem' }}>
            No entries in this period
          </div>
          <p style={{ color: '#6B879B', fontSize: '0.8rem', maxWidth: 420, margin: '6px auto 0', lineHeight: 1.6 }}>
            Approve a leave request or change a role and it will appear here.
          </p>
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div style={{
          background: 'var(--surface)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ background: 'rgba(12,36,54,0.03)' }}>
                {['When', 'Who', 'Action', 'Target', 'Change', 'IP'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '11px 16px', fontSize: '0.68rem', fontWeight: 700,
                    color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.5px',
                    borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const meta = ACTIONS[r.action] ?? { label: r.action, tone: 'blue' as const };
                const tone = TONE[meta.tone];
                const when = r.date_action ? new Date(r.date_action) : null;
                return (
                  <tr key={r.audit_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '11px 16px', color: '#34546A', whiteSpace: 'nowrap' }}>
                      <Clock size={12} style={{ verticalAlign: -1, marginRight: 5, color: '#9DB3C2' }} />
                      {when ? when.toLocaleString('en-GB', {
                        day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                      }) : '—'}
                    </td>
                    <td style={{ padding: '11px 16px', color: '#0C2436', whiteSpace: 'nowrap' }}>
                      <User size={12} style={{ verticalAlign: -1, marginRight: 5, color: '#9DB3C2' }} />
                      {r.username ?? '—'}
                      {r.role && (
                        <span style={{ color: '#9DB3C2', fontSize: '0.72rem', marginLeft: 6 }}>
                          {r.role}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '11px 16px', whiteSpace: 'nowrap' }}>
                      <span style={{
                        background: tone.bg, color: tone.color, fontSize: '0.72rem',
                        fontWeight: 700, padding: '3px 9px', borderRadius: 20,
                      }}>{meta.label}</span>
                    </td>
                    <td style={{ padding: '11px 16px', color: '#6B879B', whiteSpace: 'nowrap' }}>
                      {r.entite ? `${r.entite} #${r.entite_id ?? '—'}` : '—'}
                    </td>
                    <td style={{ padding: '11px 16px', color: '#34546A', maxWidth: 320 }}>
                      {r.ancienne_valeur && (
                        <span style={{ color: '#9DB3C2', textDecoration: 'line-through', marginRight: 6 }}>
                          {r.ancienne_valeur}
                        </span>
                      )}
                      {r.nouvelle_valeur ?? r.detail ?? '—'}
                    </td>
                    <td style={{ padding: '11px 16px', color: '#9DB3C2', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {r.adresse_ip ?? '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
