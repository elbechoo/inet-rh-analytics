'use client';
import { useState } from 'react';
import { Bot, Building2, Clock, Mail, Save, CheckCircle2 } from 'lucide-react';

const defaultConfig = {
  seuil_critique:  80,
  seuil_moyen:     50,
  seuil_retard:    40,
  jours_conge_an:  30,
  heure_entree:    '08:30',
  heure_sortie:    '17:30',
  email_digest:    '00:00',
  etl_heure:       '23:00',
  retrain_jour:    'Sunday',
  retrain_heure:   '02:00',
  gmail_user:      'inetRH@gmail.com',
  rh_email:        'responsable_rh@gmail.com',
};

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function AdminConfig() {
  const [cfg,   setCfg]   = useState(defaultConfig);
  const [saved, setSaved] = useState(false);

  const save = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const Field = ({ label, k, type = 'text', suffix = '' }: any) => (
    <div style={{ marginBottom: 18 }}>
      <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</label>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <input type={type} value={(cfg as any)[k]}
          onChange={e => setCfg(c => ({ ...c, [k]: type === 'number' ? Number(e.target.value) : e.target.value }))}
          style={{ padding: '9px 14px', borderRadius: 9, border: '1px solid var(--border)', fontSize: '0.84rem', width: 200, outline: 'none', fontFamily: 'Inter, sans-serif', boxSizing: 'border-box', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }}
          onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
          onBlur={e => (e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)')}
        />
        {suffix && <span style={{ color: '#9DB3C2', fontSize: '0.78rem', fontWeight: 600 }}>{suffix}</span>}
      </div>
    </div>
  );

  const sections = [
    {
      Icon: Bot, color: '#45B9E9', bg: 'rgba(15,163,224,0.15)',
      title: 'AI Alert Thresholds',
      content: (
        <>
          <Field label="Critical threshold (lateness %)" k="seuil_critique" type="number" suffix="%" />
          <Field label="Medium threshold (lateness %)"   k="seuil_moyen"   type="number" suffix="%" />
          <Field label="At-risk threshold (lateness %)"  k="seuil_retard"  type="number" suffix="%" />
        </>
      ),
    },
    {
      Icon: Building2, color: '#3fb950', bg: 'rgba(46,160,67,0.15)',
      title: 'HR Parameters',
      content: (
        <>
          <Field label="Leave days / year"     k="jours_conge_an" type="number" suffix="days" />
          <Field label="Normal check-in time"  k="heure_entree"   type="time" />
          <Field label="Normal check-out time" k="heure_sortie"   type="time" />
        </>
      ),
    },
    {
      Icon: Clock, color: '#45B9E9', bg: 'rgba(11,135,190,0.15)',
      title: 'APScheduler',
      content: (
        <>
          <Field label="ETL run time"    k="etl_heure"    type="time" />
          <Field label="Email digest"    k="email_digest" type="time" />
          <Field label="Retraining time" k="retrain_heure" type="time" />
          <div style={{ marginBottom: 18 }}>
            <label style={{ fontSize: '0.68rem', fontWeight: 700, color: '#6B879B', display: 'block', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Retraining day</label>
            <select value={cfg.retrain_jour} onChange={e => setCfg(c => ({ ...c, retrain_jour: e.target.value }))}
              style={{ padding: '9px 14px', borderRadius: 9, border: '1px solid var(--border)', fontSize: '0.84rem', width: 200, outline: 'none', background: 'rgba(12,36,54,0.04)', color: '#0C2436', fontFamily: 'Inter, sans-serif' }}>
              {DAYS.map(j => <option key={j}>{j}</option>)}
            </select>
          </div>
        </>
      ),
    },
    {
      Icon: Mail, color: '#e3b341', bg: 'rgba(227,179,65,0.15)',
      title: 'Email Configuration',
      content: (
        <>
          <Field label="Sender Gmail" k="gmail_user" />
          <Field label="HR recipient email" k="rh_email" />
          <div style={{ background: 'rgba(227,179,65,0.1)', border: '1px solid rgba(227,179,65,0.25)', borderRadius: 9, padding: '11px 14px', fontSize: '0.78rem', color: '#e3b341', marginTop: 4 }}>
            The Gmail App password is configured in the <code style={{ background: 'rgba(227,179,65,0.15)', padding: '1px 5px', borderRadius: 4 }}>.env</code> file.
          </div>
        </>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>

      {saved && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 999,
          background: 'rgba(46,160,67,0.2)', color: '#3fb950', border: '1px solid rgba(46,160,67,0.4)',
          padding: '12px 20px', borderRadius: 10, fontSize: '0.84rem', fontWeight: 600,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <CheckCircle2 size={15} /> Configuration saved
        </div>
      )}

      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>System Configuration</h1>
        <p style={{ color: '#6B879B', marginTop: 4, fontSize: '0.82rem' }}>HR, AI, Scheduler, and Email settings</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {sections.map(({ Icon, color, bg, title, content }, i) => (
          <div key={i} style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 24, border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <div style={{ width: 34, height: 34, borderRadius: 9, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={16} style={{ color }} />
              </div>
              <h2 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#0C2436', margin: 0 }}>{title}</h2>
            </div>
            {content}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
        <button onClick={save} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '12px 32px', borderRadius: 12, border: 'none',
          background: 'var(--brand-600)', color: 'white',
          fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
          fontFamily: 'Inter, sans-serif', boxShadow: '0 2px 10px rgba(15,163,224,0.35)',
        }}>
          <Save size={15} /> Save configuration
        </button>
      </div>
    </div>
  );
}
