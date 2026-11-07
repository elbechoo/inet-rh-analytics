'use client';
import { useEffect, useState } from 'react';
import { Building2, Plus, Pencil, Trash2, X } from 'lucide-react';
import { authFetch } from '@/app/lib/api';

export default function AdminDepts() {
  const [depts,   setDepts]   = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast,   setToast]   = useState<{ text: string; ok: boolean } | null>(null);
  const [modal,   setModal]   = useState<'create' | 'edit' | null>(null);
  const [editing, setEditing] = useState<any>(null);
  const [form,    setForm]    = useState({ nom_departement: '', sous_departement: '' });

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const load = () => {
    authFetch('/api/admin/depts').then(r => r.json()).then(d => { setDepts(d); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setForm({ nom_departement: '', sous_departement: '' });
    setEditing(null);
    setModal('create');
  };

  const openEdit = (d: any) => {
    setForm({ nom_departement: d.nom_departement, sous_departement: d.sous_departement || '' });
    setEditing(d);
    setModal('edit');
  };

  const save = async () => {
    if (!form.nom_departement.trim()) return;
    if (modal === 'create') {
      await authFetch('/api/admin/depts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      showToast('Department created');
    } else {
      await authFetch(`/api/admin/depts/${editing.departement_id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      showToast('Department updated');
    }
    setModal(null);
    load();
  };

  const del = async (d: any) => {
    if (!confirm(`Delete "${d.nom_departement}"?`)) return;
    const res  = await authFetch(`/api/admin/depts/${d.departement_id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Cannot delete department', false); return; }
    showToast('Department deleted');
    load();
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 999,
          background: toast.ok ? 'rgba(46,160,67,0.2)' : 'rgba(248,81,73,0.2)',
          color: toast.ok ? '#3fb950' : '#f85149',
          border: `1px solid ${toast.ok ? 'rgba(46,160,67,0.4)' : 'rgba(248,81,73,0.4)'}`,
          padding: '12px 20px', borderRadius: 10, fontSize: '0.84rem', fontWeight: 600,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        }}>
          {toast.text}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'var(--surface)', borderRadius: 16, padding: 32, width: 460, boxShadow: '0 20px 60px rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <h2 style={{ margin: 0, color: '#0C2436', fontSize: '1.1rem', fontWeight: 700 }}>
                {modal === 'create' ? 'New Department' : 'Edit Department'}
              </h2>
              <button onClick={() => setModal(null)} style={{ border: 'none', background: 'rgba(12,36,54,0.04)', borderRadius: 7, padding: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                <X size={15} color="#6B879B" />
              </button>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Department name *</label>
              <input value={form.nom_departement} onChange={e => setForm(f => ({ ...f, nom_departement: e.target.value }))}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 9, border: '1px solid var(--border)', fontSize: '0.84rem', boxSizing: 'border-box', outline: 'none', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }}
                onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
                onBlur={e => (e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)')}
              />
            </div>
            <div style={{ marginBottom: 28 }}>
              <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Sub-department</label>
              <input value={form.sous_departement} onChange={e => setForm(f => ({ ...f, sous_departement: e.target.value }))}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 9, border: '1px solid var(--border)', fontSize: '0.84rem', boxSizing: 'border-box', outline: 'none', fontFamily: 'Inter, sans-serif', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }}
                onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
                onBlur={e => (e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)')}
              />
            </div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button onClick={() => setModal(null)} style={{ padding: '10px 20px', borderRadius: 9, border: '1px solid var(--border)', background: 'rgba(12,36,54,0.04)', color: '#6B879B', cursor: 'pointer', fontSize: '0.84rem', fontFamily: 'Inter, sans-serif' }}>
                Cancel
              </button>
              <button onClick={save} style={{ padding: '10px 24px', borderRadius: 9, border: 'none', background: 'var(--brand-600)', color: 'white', fontWeight: 700, cursor: 'pointer', fontSize: '0.84rem', fontFamily: 'Inter, sans-serif', boxShadow: 'none' }}>
                {modal === 'create' ? 'Create' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>Departments</h1>
          <p style={{ color: '#6B879B', marginTop: 4, fontSize: '0.82rem' }}>{depts.length} departments</p>
        </div>
        <button onClick={openCreate} style={{
          display: 'flex', alignItems: 'center', gap: 7,
          background: 'var(--brand-600)', color: 'white',
          border: 'none', borderRadius: 10, padding: '10px 18px',
          fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
          fontFamily: 'Inter, sans-serif', boxShadow: 'none',
        }}>
          <Plus size={15} /> New department
        </button>
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {loading ? (
          <div style={{ color: '#9DB3C2', fontSize: '0.84rem' }}>Loading...</div>
        ) : depts.length === 0 ? (
          <div style={{ color: '#9DB3C2', fontSize: '0.84rem', padding: 20 }}>No departments yet</div>
        ) : depts.map(d => (
          <div key={d.departement_id} style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 22, border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', transition: 'box-shadow 0.15s, border-color 0.15s' }}
            onMouseEnter={ev => { ev.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.4)'; ev.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; }}
            onMouseLeave={ev => { ev.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.3)'; ev.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)'; }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <div style={{ width: 38, height: 38, borderRadius: 10, background: 'rgba(15,163,224,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Building2 size={17} color="#45B9E9" />
                </div>
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#0C2436' }}>{d.nom_departement}</div>
                  {d.sous_departement && <div style={{ fontSize: '0.72rem', color: '#9DB3C2', marginTop: 2 }}>{d.sous_departement}</div>}
                </div>
              </div>
              <span style={{ background: 'rgba(15,163,224,0.15)', color: '#45B9E9', borderRadius: 20, padding: '3px 10px', fontSize: '0.70rem', fontWeight: 700, flexShrink: 0 }}>
                {d.nb_employes} emp.
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#9DB3C2', marginBottom: 16 }}>Created {d.date_creation || '-'}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => openEdit(d)} style={{ flex: 1, padding: '8px', borderRadius: 8, border: '1px solid var(--border)', background: 'rgba(12,36,54,0.04)', color: '#34546A', fontSize: '0.78rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, fontFamily: 'Inter, sans-serif' }}>
                <Pencil size={12} /> Edit
              </button>
              <button onClick={() => del(d)} style={{ flex: 1, padding: '8px', borderRadius: 8, border: '1.5px solid rgba(248,81,73,0.3)', background: 'rgba(248,81,73,0.1)', color: '#f85149', fontSize: '0.78rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, fontFamily: 'Inter, sans-serif' }}>
                <Trash2 size={12} /> Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
