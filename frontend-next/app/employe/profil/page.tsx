'use client';
import { useEffect, useState } from 'react';
import { User, Mail, Briefcase, FileText, Calendar, Zap } from 'lucide-react';

export default function MonProfil() {
  const [user, setUser] = useState<any>(null);
  const [solde, setSolde] = useState<any>({});

  useEffect(() => {
    const u = JSON.parse(localStorage.getItem('inet_user') || '{}');
    setUser(u);
    const id = u?.employe?.employe_id;
    if (id) fetch(`/api/conges/solde/${id}`).then(r => r.json()).then(d => setSolde(d || {}));
  }, []);

  const emp = user?.employe || {};
  const sr  = solde.solde_restant ?? 0;
  const sa  = solde.solde_annuel ?? 30;
  const pct = sa ? Math.round((solde.solde_utilise ?? 0) / sa * 100) : 0;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>My Profile</h1>
        <p style={{ color: '#6B879B', fontSize: '0.82rem', margin: '4px 0 0' }}>Personal information and leave balance</p>
      </div>

      {/* Hero card */}
      <div style={{ background: 'linear-gradient(135deg,#0B87BE 0%,#0FA3E0 60%,#45B9E9 100%)', borderRadius: 16, padding: '24px 28px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 20, boxShadow: '0 4px 20px rgba(15,163,224,0.3)' }}>
        <div style={{ width: 72, height: 72, borderRadius: 16, background: 'rgba(255,255,255,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem', fontWeight: 700, color: 'white', flexShrink: 0, border: '2px solid rgba(255,255,255,0.3)' }}>
          {emp.prenom?.[0]}{emp.nom?.[0]}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'white', letterSpacing: '-0.3px' }}>{emp.prenom} {emp.nom}</div>
          <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem', marginTop: 2 }}>{emp.poste}</div>
          <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.75rem', marginTop: 4, fontFamily: 'monospace' }}>{emp.matricule}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 8, padding: '6px 12px' }}>
          <Zap size={13} color="rgba(255,255,255,0.7)" />
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.72rem', fontWeight: 600 }}>Employee</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Info card */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 7 }}>
            <User size={14} color="#6B879B" /> Personal Information
          </div>
          {[
            { label: 'Full name',    value: `${emp.prenom} ${emp.nom}`, Icon: User },
            { label: 'Email',        value: emp.adresse_mail,           Icon: Mail },
            { label: 'Employee ID',  value: emp.matricule,              Icon: FileText },
            { label: 'Position',     value: emp.poste,                  Icon: Briefcase },
            { label: 'Contract',     value: emp.type_contrat,           Icon: FileText },
            { label: 'Hire date',    value: emp.date_embauche,          Icon: Calendar },
            { label: 'Status',       value: emp.statut,                 Icon: User },
          ].map((row, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < 6 ? '1px solid rgba(12,36,54,0.04)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <row.Icon size={13} color="#9DB3C2" />
                <span style={{ fontSize: '0.76rem', color: '#6B879B' }}>{row.label}</span>
              </div>
              <span style={{ fontSize: '0.76rem', fontWeight: 600, color: '#0C2436' }}>{row.value || '-'}</span>
            </div>
          ))}
        </div>

        {/* Leave balance */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0C2436', marginBottom: 14 }}>
            Leave Balance {new Date().getFullYear()}
          </div>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '4rem', fontWeight: 700, color: '#45B9E9', lineHeight: 1 }}>{sr}</div>
            <div style={{ fontSize: '0.82rem', color: '#9DB3C2', marginTop: 6 }}>days remaining</div>
          </div>
          <div style={{ background: 'rgba(12,36,54,0.04)', borderRadius: 99, height: 10, marginBottom: 16, overflow: 'hidden' }}>
            <div style={{ background: 'linear-gradient(90deg,#0FA3E0,#0B87BE)', width: `${pct}%`, height: 10, borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-around' }}>
            {[
              { label: 'Total', value: `${sa}d`,                    color: '#0C2436' },
              { label: 'Used',  value: `${solde.solde_utilise ?? 0}d`, color: '#f85149' },
              { label: 'Left',  value: `${sr}d`,                    color: '#3fb950' },
            ].map((k, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: k.color }}>{k.value}</div>
                <div style={{ fontSize: '0.65rem', color: '#9DB3C2', fontWeight: 600, textTransform: 'uppercase', marginTop: 2 }}>{k.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
