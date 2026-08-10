'use client';
import { useEffect, useState } from 'react';
import {
  Users, Search, Plus, Pencil, Trash2, CheckCircle, XCircle, X,
} from 'lucide-react';

type Dept = { departement_id: number; nom_departement: string };

export default function GestionEmployes() {
  const [employes, setEmployes] = useState<any[]>([]);
  const [search,   setSearch]   = useState('');
  const [loading,  setLoading]  = useState(true);

  // Add-employee modal state
  const [showAdd,  setShowAdd]    = useState(false);
  const [depts,    setDepts]      = useState<Dept[]>([]);
  const [saving,   setSaving]     = useState(false);
  const [formErr,  setFormErr]    = useState<string | null>(null);
  const blankForm = {
    matricule: '', nom: '', prenom: '', adresse_mail: '',
    date_naissance: '', sexe: 'M', date_embauche: '',
    poste: '', type_contrat: 'CDI', departement_id: '',
    role: 'employe', password: '',
  };
  const [form, setForm] = useState(blankForm);

  const loadEmployes = () => {
    setLoading(true);
    fetch('/api/employes/', { cache: 'no-store' })
      .then(r => r.json())
      .then(d => { setEmployes(d || []); setLoading(false); })
      .catch(() => setLoading(false));
  };
  useEffect(loadEmployes, []);

  // Load departments once for the modal dropdown (deduped by name).
  useEffect(() => {
    fetch('/api/employes/departements/all', { cache: 'no-store' })
      .then(r => r.json())
      .then((d: Dept[]) => {
        const seen = new Set<string>();
        const unique: Dept[] = [];
        for (const dep of (d || [])) {
          if (!seen.has(dep.nom_departement)) {
            seen.add(dep.nom_departement);
            unique.push(dep);
          }
        }
        setDepts(unique);
      })
      .catch(() => {});
  }, []);

  const openAdd = () => {
    // Pre-fill a sane matricule suggestion (max+1 padded to 5 digits).
    const maxId = employes.reduce((m, e) => {
      const n = parseInt(String(e.matricule || '').replace(/\D/g, ''), 10);
      return Number.isFinite(n) && n > m ? n : m;
    }, 0);
    setForm({
      ...blankForm,
      matricule: String(maxId + 1).padStart(5, '0'),
      date_embauche: new Date().toISOString().slice(0, 10),
      departement_id: depts[0]?.departement_id?.toString() ?? '',
    });
    setFormErr(null);
    setShowAdd(true);
  };

  const submitAdd = async () => {
    setFormErr(null);
    const required = ['matricule', 'nom', 'prenom', 'adresse_mail', 'date_embauche', 'departement_id', 'password'];
    for (const k of required) {
      if (!String((form as any)[k] || '').trim()) {
        setFormErr(`Field "${k}" is required`);
        return;
      }
    }
    if (form.password.length < 4) {
      setFormErr('Password must be at least 4 characters');
      return;
    }
    setSaving(true);
    try {
      const payload: any = { ...form, departement_id: parseInt(form.departement_id, 10) };
      if (!payload.date_naissance) delete payload.date_naissance;
      if (!payload.sexe)           delete payload.sexe;
      if (!payload.poste)          delete payload.poste;
      const res = await fetch('/api/employes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setFormErr(body?.detail || `Server returned ${res.status}`);
        setSaving(false);
        return;
      }
      setShowAdd(false);
      setSaving(false);
      loadEmployes();   // refresh the table
    } catch (err: any) {
      setFormErr(err?.message || 'Network error');
      setSaving(false);
    }
  };

  const filtered = employes.filter(e =>
    `${e.nom} ${e.prenom} ${e.matricule} ${e.poste}`.toLowerCase().includes(search.toLowerCase())
  );

  const stats = [
    { label: 'Total',      value: employes.length,                                      color: '#45B9E9', dimBg: 'rgba(15,163,224,0.15)' },
    { label: 'Active',     value: employes.filter(e => e.statut === 'Actif').length,     color: '#3fb950', dimBg: 'rgba(46,160,67,0.15)' },
    { label: 'Permanent',  value: employes.filter(e => e.type_contrat === 'CDI').length, color: '#45B9E9', dimBg: 'rgba(69,185,233,0.15)' },
    { label: 'Fixed-term', value: employes.filter(e => e.type_contrat === 'CDD').length, color: '#e3b341', dimBg: 'rgba(227,179,65,0.15)' },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Employee Management</h1>
          <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>{employes.length} employees registered</p>
        </div>
        <button
          onClick={openAdd}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            background: 'var(--brand-600)', color: 'white',
            border: 'none', borderRadius: 10, padding: '10px 18px',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'Inter, sans-serif',
            boxShadow: '0 2px 8px rgba(15,163,224,0.4)',
          }}
        >
          <Plus size={16} /> Add employee
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 22 }}>
        {stats.map((s, i) => (
          <div key={i} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '18px 20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: s.dimBg, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
              <Users size={17} style={{ color: s.color }} />
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontSize: '0.68rem', color: '#6B879B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 16, display: 'flex', alignItems: 'center', overflow: 'hidden', transition: 'border-color 0.15s, box-shadow 0.15s' }}
        onFocusCapture={e => { (e.currentTarget as HTMLDivElement).style.borderColor = '#0FA3E0'; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 0 0 3px rgba(15,163,224,0.15)'; }}
        onBlurCapture={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(12,36,54,0.04)'; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; }}
      >
        <div style={{ padding: '0 14px', color: '#9DB3C2', display: 'flex' }}>
          <Search size={16} />
        </div>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search by name, employee ID, position..."
          style={{ flex: 1, border: 'none', outline: 'none', fontSize: '0.875rem', color: '#0C2436', background: 'transparent', padding: '12px 0', fontFamily: 'Inter, sans-serif', width: '100%' }}
        />
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436' }}>Employee list</span>
          <span style={{ fontSize: '0.72rem', color: '#6B879B', background: 'rgba(12,36,54,0.04)', padding: '3px 10px', borderRadius: 20 }}>{filtered.length} result{filtered.length !== 1 ? 's' : ''}</span>
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2', fontSize: '0.85rem' }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#9DB3C2', fontSize: '0.85rem' }}>No employees found</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'rgba(12,36,54,0.04)' }}>
                  {['Employee ID', 'Full Name', 'Email', 'Position', 'Contract', 'Status', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.66rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.6px', whiteSpace: 'nowrap', borderBottom: '1px solid rgba(12,36,54,0.04)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((e, i) => (
                  <tr key={i} style={{ transition: 'background 0.1s' }}
                    onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(12,36,54,0.04)')}
                    onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '0.75rem', color: '#6B879B', fontFamily: 'monospace', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{e.matricule}</td>
                    <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--brand-600)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                          {e.prenom?.[0]}{e.nom?.[0]}
                        </div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0C2436' }}>{e.prenom} {e.nom}</div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#6B879B', borderTop: '1px solid rgba(12,36,54,0.04)' }}>{e.adresse_mail || '—'}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.78rem', color: '#34546A', fontWeight: 500, borderTop: '1px solid rgba(12,36,54,0.04)' }}>{e.poste || '—'}</td>
                    <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                      <span style={{ background: 'rgba(12,36,54,0.04)', color: '#34546A', padding: '3px 10px', borderRadius: 6, fontSize: '0.72rem', fontWeight: 600 }}>{e.type_contrat || '—'}</span>
                    </td>
                    <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                      {e.statut === 'Actif' ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#3fb950' }}>
                          <CheckCircle size={13} />
                          <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>Active</span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#f85149' }}>
                          <XCircle size={13} />
                          <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>Inactive</span>
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px', borderTop: '1px solid rgba(12,36,54,0.04)' }}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button style={{ background: 'rgba(15,163,224,0.15)', border: 'none', borderRadius: 7, padding: '6px 8px', cursor: 'pointer', display: 'flex', transition: 'background 0.12s' }}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(15,163,224,0.25)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(15,163,224,0.15)')}
                        >
                          <Pencil size={13} color="#45B9E9" />
                        </button>
                        <button style={{ background: 'rgba(248,81,73,0.15)', border: 'none', borderRadius: 7, padding: '6px 8px', cursor: 'pointer', display: 'flex', transition: 'background 0.12s' }}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(248,81,73,0.25)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(248,81,73,0.15)')}
                        >
                          <Trash2 size={13} color="#f85149" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Add Employee modal ────────────────────────────────────────── */}
      {showAdd && (
        <div
          onClick={() => !saving && setShowAdd(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: 20, fontFamily: 'Inter, sans-serif',
          }}
        >
          <div
            onClick={ev => ev.stopPropagation()}
            style={{
              width: '100%', maxWidth: 640, background: 'var(--surface)',
              border: '1px solid var(--border)', borderRadius: 16,
              boxShadow: '0 24px 60px rgba(0,0,0,0.6)', overflow: 'hidden',
              display: 'flex', flexDirection: 'column', maxHeight: '90vh',
            }}
          >
            {/* header */}
            <div style={{ padding: '18px 22px', borderBottom: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0C2436' }}>New employee</div>
                <div style={{ fontSize: '0.78rem', color: '#6B879B', marginTop: 2 }}>Create an account in HR + user portal</div>
              </div>
              <button
                onClick={() => !saving && setShowAdd(false)}
                style={{ background: 'rgba(12,36,54,0.04)', border: 'none', borderRadius: 8, padding: 6, cursor: 'pointer', display: 'flex' }}
                aria-label="Close"
              >
                <X size={16} color="#34546A" />
              </button>
            </div>

            {/* body */}
            <div style={{ padding: '20px 22px', overflowY: 'auto' }}>
              <FormGrid>
                <Field label="Employee ID *">
                  <Input value={form.matricule}
                         onChange={v => setForm(f => ({ ...f, matricule: v }))} />
                </Field>
                <Field label="Email *">
                  <Input type="email" value={form.adresse_mail}
                         onChange={v => setForm(f => ({ ...f, adresse_mail: v }))} />
                </Field>

                <Field label="First name *">
                  <Input value={form.prenom}
                         onChange={v => setForm(f => ({ ...f, prenom: v }))} />
                </Field>
                <Field label="Last name *">
                  <Input value={form.nom}
                         onChange={v => setForm(f => ({ ...f, nom: v }))} />
                </Field>

                <Field label="Date of birth">
                  <Input type="date" value={form.date_naissance}
                         onChange={v => setForm(f => ({ ...f, date_naissance: v }))} />
                </Field>
                <Field label="Gender">
                  <Select value={form.sexe}
                          onChange={v => setForm(f => ({ ...f, sexe: v }))}
                          options={[['M', 'Male'], ['F', 'Female']]} />
                </Field>

                <Field label="Hiring date *">
                  <Input type="date" value={form.date_embauche}
                         onChange={v => setForm(f => ({ ...f, date_embauche: v }))} />
                </Field>
                <Field label="Department *">
                  <Select value={form.departement_id}
                          onChange={v => setForm(f => ({ ...f, departement_id: v }))}
                          options={[['', '— Select —'], ...depts.map(d => [String(d.departement_id), d.nom_departement] as [string, string])]} />
                </Field>

                <Field label="Position">
                  <Input value={form.poste}
                         onChange={v => setForm(f => ({ ...f, poste: v }))}
                         placeholder="e.g. Software Engineer" />
                </Field>
                <Field label="Contract type">
                  <Select value={form.type_contrat}
                          onChange={v => setForm(f => ({ ...f, type_contrat: v }))}
                          options={[['CDI', 'CDI — Permanent'], ['CDD', 'CDD — Fixed-term'], ['Stage', 'Stage — Internship']]} />
                </Field>

                <Field label="Portal role">
                  <Select value={form.role}
                          onChange={v => setForm(f => ({ ...f, role: v }))}
                          options={[['employe', 'Employee'], ['hr_manager', 'HR Manager'], ['admin', 'Administrator']]} />
                </Field>
                <Field label="Temporary password *">
                  <Input type="text" value={form.password}
                         onChange={v => setForm(f => ({ ...f, password: v }))}
                         placeholder="Min. 4 characters" />
                </Field>
              </FormGrid>

              {formErr && (
                <div style={{
                  marginTop: 14, padding: '10px 14px', borderRadius: 8,
                  background: 'rgba(248,81,73,0.12)', border: '1px solid rgba(248,81,73,0.35)',
                  color: '#fca5a5', fontSize: '0.82rem',
                }}>
                  {formErr}
                </div>
              )}
            </div>

            {/* footer */}
            <div style={{ padding: '14px 22px', borderTop: '1px solid rgba(12,36,54,0.04)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => !saving && setShowAdd(false)}
                disabled={saving}
                style={{
                  background: 'rgba(12,36,54,0.04)', color: '#34546A',
                  border: 'none', borderRadius: 9, padding: '9px 16px',
                  fontWeight: 600, fontSize: '0.84rem', cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.5 : 1,
                }}
              >
                Cancel
              </button>
              <button
                onClick={submitAdd}
                disabled={saving}
                style={{
                  background: 'var(--brand-600)', color: 'white',
                  border: 'none', borderRadius: 9, padding: '9px 18px',
                  fontWeight: 700, fontSize: '0.84rem', cursor: saving ? 'progress' : 'pointer',
                  boxShadow: '0 2px 8px rgba(15,163,224,0.4)',
                  opacity: saving ? 0.7 : 1,
                  display: 'flex', alignItems: 'center', gap: 7,
                }}
              >
                {saving ? 'Saving…' : (<><Plus size={14} /> Create employee</>)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ── tiny form primitives, kept local so we don't pollute the design system ──
function FormGrid({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 16px' }}>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#6B879B', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</span>
      {children}
    </label>
  );
}

function Input({
  value, onChange, type = 'text', placeholder,
}: { value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return (
    <input
      type={type} value={value} placeholder={placeholder}
      onChange={ev => onChange(ev.target.value)}
      style={{
        background: '#F2F7FB', border: '1.5px solid rgba(255,255,255,0.10)',
        borderRadius: 8, padding: '9px 12px', color: '#0C2436',
        fontSize: '0.85rem', outline: 'none', fontFamily: 'Inter, sans-serif',
        transition: 'border-color 0.12s, box-shadow 0.12s',
      }}
      onFocus={e => { e.currentTarget.style.borderColor = '#0FA3E0'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(15,163,224,0.15)'; }}
      onBlur ={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.10)'; e.currentTarget.style.boxShadow = 'none'; }}
    />
  );
}

function Select({
  value, onChange, options,
}: { value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <select
      value={value} onChange={ev => onChange(ev.target.value)}
      style={{
        background: '#F2F7FB', border: '1.5px solid rgba(255,255,255,0.10)',
        borderRadius: 8, padding: '9px 12px', color: '#0C2436',
        fontSize: '0.85rem', outline: 'none', fontFamily: 'Inter, sans-serif',
        appearance: 'none', cursor: 'pointer',
      }}
      onFocus={e => { e.currentTarget.style.borderColor = '#0FA3E0'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(15,163,224,0.15)'; }}
      onBlur ={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.10)'; e.currentTarget.style.boxShadow = 'none'; }}
    >
      {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  );
}
