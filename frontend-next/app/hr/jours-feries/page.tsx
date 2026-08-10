'use client';
import { useEffect, useState } from 'react';
import { CalendarDays, Plus, ArrowLeft, Trash2, Pencil, Check, X, Sparkles, Info } from 'lucide-react';

type Holiday = {
  jour_ferie_id: number;
  date_ferie: string;
  nom: string;
  type_ferie: string;
  chome: boolean;
};

const TYPE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  civil:      { bg: 'rgba(15,163,224,0.13)', color: '#0B87BE', label: 'Civil' },
  religieux:  { bg: 'rgba(18,165,148,0.14)', color: '#0E8C7E', label: 'Religious' },
  entreprise: { bg: 'rgba(245,158,11,0.15)', color: '#B45309', label: 'Company' },
};

export default function JoursFeries() {
  const currentYear = new Date().getFullYear();

  const [items,   setItems]   = useState<Holiday[]>([]);
  const [years,   setYears]   = useState<{ year: number; count: number }[]>([]);
  const [year,    setYear]    = useState(currentYear);
  const [loading, setLoading] = useState(true);
  const [tab,     setTab]     = useState<'list' | 'create'>('list');
  const [editing, setEditing] = useState<number | null>(null);
  const [draft,   setDraft]   = useState('');
  const [msg,     setMsg]     = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);
  const [form,    setForm]    = useState({ date_ferie: '', nom: '', type_ferie: 'entreprise', chome: true });

  useEffect(() => { load(); }, [year]);

  function flash(kind: 'ok' | 'err', text: string) {
    setMsg({ kind, text });
    setTimeout(() => setMsg(null), 4000);
  }

  async function load() {
    setLoading(true);
    try {
      const [h, y] = await Promise.all([
        fetch(`/api/holidays/?year=${year}`, { credentials: 'include' }).then(r => r.json()),
        fetch('/api/holidays/years', { credentials: 'include' }).then(r => r.json()),
      ]);
      setItems(Array.isArray(h) ? h : []);
      setYears(Array.isArray(y) ? y : []);
    } catch {
      flash('err', 'Could not load the calendar.');
    } finally {
      setLoading(false);
    }
  }

  async function create() {
    if (!form.date_ferie || !form.nom.trim()) { flash('err', 'Date and name are required.'); return; }
    const res = await fetch('/api/holidays/', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      flash('err', d.detail || 'Could not add that day.');
      return;
    }
    setForm({ date_ferie: '', nom: '', type_ferie: 'entreprise', chome: true });
    setTab('list');
    flash('ok', 'Day added.');
    load();
  }

  async function saveName(id: number) {
    if (!draft.trim()) return;
    const res = await fetch(`/api/holidays/${id}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nom: draft }),
    });
    setEditing(null);
    if (res.ok) { flash('ok', 'Updated.'); load(); } else flash('err', 'Update failed.');
  }

  async function toggleChome(h: Holiday) {
    const res = await fetch(`/api/holidays/${h.jour_ferie_id}`, {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chome: !h.chome }),
    });
    if (res.ok) load(); else flash('err', 'Update failed.');
  }

  async function remove(h: Holiday) {
    if (!confirm(`Remove ${h.nom} (${h.date_ferie}) from the calendar?\n\nLeave taken on this date will start counting against employees' balances again.`)) return;
    const res = await fetch(`/api/holidays/${h.jour_ferie_id}`, { method: 'DELETE', credentials: 'include' });
    if (res.ok) { flash('ok', 'Removed.'); load(); } else flash('err', 'Could not remove it.');
  }

  async function seedYear() {
    const res = await fetch(`/api/holidays/seed/${year}`, { method: 'POST', credentials: 'include' });
    const d = await res.json().catch(() => ({}));
    if (res.ok) { flash('ok', d.message || 'Calendar generated.'); load(); }
    else flash('err', d.detail || 'Could not generate the calendar.');
  }

  const offDays = items.filter(h => h.chome).length;
  const worked  = items.length - offDays;

  const yearOptions = Array.from(
    new Set([...years.map(y => y.year), currentYear, currentYear + 1, currentYear + 2])
  ).sort();

  const kpis = [
    { label: 'Days in calendar', value: items.length, color: '#0B87BE', dimBg: 'rgba(15,163,224,0.15)' },
    { label: 'Non-working',      value: offDays,      color: '#0E8C7E', dimBg: 'rgba(18,165,148,0.15)' },
    { label: 'Marked as worked', value: worked,       color: '#B45309', dimBg: 'rgba(245,158,11,0.15)' },
  ];

  const inputStyle: React.CSSProperties = {
    width: '100%', border: '1px solid var(--border)', borderRadius: 8, padding: '9px 12px',
    fontSize: '0.84rem', outline: 'none', boxSizing: 'border-box',
    fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436',
  };
  const labelStyle: React.CSSProperties = {
    fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block',
    marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px',
  };

  return (
    <div className="view-enter" style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>
            Public Holidays
          </h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>
            Days excluded from leave deduction and absence detection
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select value={year} onChange={e => setYear(Number(e.target.value))}
            style={{ ...inputStyle, width: 'auto', fontWeight: 600, cursor: 'pointer' }}>
            {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
          <button onClick={() => setTab(tab === 'create' ? 'list' : 'create')} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: tab === 'create' ? '#FFFFFF' : 'var(--brand-600)',
            color: tab === 'create' ? '#34546A' : 'white',
            border: tab === 'create' ? '1.5px solid rgba(12,36,54,0.04)' : 'none',
            borderRadius: 10, padding: '10px 18px', fontWeight: 600, fontSize: '0.85rem',
            cursor: 'pointer', fontFamily: 'Inter, sans-serif',
            boxShadow: tab === 'create' ? 'none' : '0 2px 8px rgba(15,163,224,0.3)',
          }}>
            {tab === 'create' ? <><ArrowLeft size={15} /> Back</> : <><Plus size={15} /> Add a day</>}
          </button>
        </div>
      </div>

      {msg && (
        <div className="animate-fadein" style={{
          marginBottom: 16, padding: '10px 14px', borderRadius: 9, fontSize: '0.82rem',
          background: msg.kind === 'ok' ? 'rgba(18,165,148,0.10)' : '#FDECEC',
          border: `1px solid ${msg.kind === 'ok' ? 'rgba(18,165,148,0.25)' : '#F8D5D5'}`,
          color: msg.kind === 'ok' ? '#0E7C6F' : '#B01C1C',
        }}>
          {msg.text}
        </div>
      )}

      {/* KPIs */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
        {kpis.map((k, i) => (
          <div key={i} style={{
            flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)',
            padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)',
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 9, background: k.dimBg, display: 'flex',
              alignItems: 'center', justifyContent: 'center', marginBottom: 10,
            }}>
              <CalendarDays size={17} style={{ color: k.color }} />
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: k.color, lineHeight: 1 }}>{k.value}</div>
            <div style={{
              fontSize: '0.68rem', color: '#6B879B', fontWeight: 700,
              textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4,
            }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Create form */}
      {tab === 'create' && (
        <div className="animate-fadein" style={{
          background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 24,
          border: '1px solid var(--border)', marginBottom: 20, boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0C2436', marginBottom: 18 }}>
            Add a non-working day
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={labelStyle}>Date *</label>
              <input type="date" value={form.date_ferie} style={inputStyle}
                onChange={e => setForm({ ...form, date_ferie: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Name *</label>
              <input type="text" placeholder="e.g. Annual company closure" value={form.nom} style={inputStyle}
                onChange={e => setForm({ ...form, nom: e.target.value })} />
            </div>
            <div>
              <label style={labelStyle}>Type</label>
              <select value={form.type_ferie} style={inputStyle}
                onChange={e => setForm({ ...form, type_ferie: e.target.value })}>
                <option value="entreprise">Company closure</option>
                <option value="civil">Civil holiday</option>
                <option value="religieux">Religious holiday</option>
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 2 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem', color: '#34546A', cursor: 'pointer' }}>
                <input type="checkbox" checked={form.chome}
                  onChange={e => setForm({ ...form, chome: e.target.checked })} />
                Non-working day
              </label>
            </div>
          </div>
          <button onClick={create} style={{
            marginTop: 18, background: 'var(--brand-600)', color: 'white', border: 'none',
            borderRadius: 10, padding: '10px 20px', fontWeight: 600, fontSize: '0.85rem',
            cursor: 'pointer', fontFamily: 'Inter, sans-serif',
          }}>
            Add day
          </button>
        </div>
      )}

      {/* Empty year */}
      {!loading && items.length === 0 && (
        <div style={{
          background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '48px 24px',
          border: '1px solid var(--border)', textAlign: 'center', boxShadow: 'var(--shadow-sm)',
        }}>
          <CalendarDays size={26} style={{ color: '#9DB3C2', marginBottom: 12 }} />
          <div style={{ fontWeight: 600, color: '#34546A', fontSize: '0.9rem' }}>
            No calendar for {year}
          </div>
          <p style={{ color: '#6B879B', fontSize: '0.8rem', maxWidth: 420, margin: '6px auto 18px', lineHeight: 1.6 }}>
            Without a calendar, public holidays are counted as ordinary working days —
            leave taken across them is deducted from employees&apos; balances.
          </p>
          <button onClick={seedYear} style={{
            display: 'inline-flex', alignItems: 'center', gap: 7, background: 'var(--brand-600)',
            color: 'white', border: 'none', borderRadius: 10, padding: '10px 20px',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'Inter, sans-serif',
          }}>
            <Sparkles size={15} /> Generate {year} calendar
          </button>
        </div>
      )}

      {/* Table */}
      {items.length > 0 && (
        <div style={{
          background: 'var(--surface)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
            <thead>
              <tr style={{ background: 'rgba(12,36,54,0.03)' }}>
                {['Date', 'Day', 'Name', 'Type', 'Status', ''].map((h, i) => (
                  <th key={i} style={{
                    textAlign: i === 5 ? 'right' : 'left', padding: '11px 16px',
                    fontSize: '0.68rem', fontWeight: 700, color: '#6B879B',
                    textTransform: 'uppercase', letterSpacing: '0.5px',
                    borderBottom: '1px solid var(--border)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(h => {
                const d = new Date(h.date_ferie + 'T00:00:00');
                const weekend = d.getDay() === 0 || d.getDay() === 6;
                const style = TYPE_STYLE[h.type_ferie] || TYPE_STYLE.civil;
                return (
                  <tr key={h.jour_ferie_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '11px 16px', fontWeight: 600, color: '#0C2436', whiteSpace: 'nowrap' }}>
                      {h.date_ferie}
                    </td>
                    <td style={{ padding: '11px 16px', color: weekend ? '#9DB3C2' : '#34546A' }}>
                      {d.toLocaleDateString('en-GB', { weekday: 'short' })}
                      {weekend && <span style={{ fontSize: '0.7rem', marginLeft: 6 }}>weekend</span>}
                    </td>
                    <td style={{ padding: '11px 16px', color: '#34546A' }}>
                      {editing === h.jour_ferie_id ? (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <input value={draft} onChange={e => setDraft(e.target.value)}
                            style={{ ...inputStyle, padding: '5px 9px' }}
                            onKeyDown={e => { if (e.key === 'Enter') saveName(h.jour_ferie_id); if (e.key === 'Escape') setEditing(null); }} />
                          <button onClick={() => saveName(h.jour_ferie_id)} title="Save"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#0E8C7E', display: 'flex' }}>
                            <Check size={15} />
                          </button>
                          <button onClick={() => setEditing(null)} title="Cancel"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9DB3C2', display: 'flex' }}>
                            <X size={15} />
                          </button>
                        </div>
                      ) : h.nom}
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <span style={{
                        background: style.bg, color: style.color, fontSize: '0.7rem', fontWeight: 700,
                        padding: '3px 9px', borderRadius: 20,
                      }}>{style.label}</span>
                    </td>
                    <td style={{ padding: '11px 16px' }}>
                      <button onClick={() => toggleChome(h)} title="Click to toggle"
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                          fontSize: '0.78rem', fontWeight: 600,
                          color: h.chome ? '#0E8C7E' : '#B45309',
                        }}>
                        {h.chome ? 'Non-working' : 'Worked'}
                      </button>
                    </td>
                    <td style={{ padding: '11px 16px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <button onClick={() => { setEditing(h.jour_ferie_id); setDraft(h.nom); }} title="Rename"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6B879B', padding: 5 }}>
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => remove(h)} title="Remove"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#C2410C', padding: 5 }}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Note on Islamic dates */}
      {items.some(h => h.type_ferie === 'religieux') && (
        <div style={{
          marginTop: 16, display: 'flex', gap: 10, alignItems: 'flex-start',
          background: 'rgba(15,163,224,0.06)', border: '1px solid rgba(15,163,224,0.18)',
          borderRadius: 10, padding: '12px 14px', fontSize: '0.78rem',
          color: '#34546A', lineHeight: 1.6,
        }}>
          <Info size={15} style={{ color: '#0B87BE', flexShrink: 0, marginTop: 1 }} />
          <span>
            Religious holidays are set by moon sighting and are usually confirmed only days in advance.
            Dates shown for future years are estimates — correct them here once the official
            announcement is published.
          </span>
        </div>
      )}
    </div>
  );
}
