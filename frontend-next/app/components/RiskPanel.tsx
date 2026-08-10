'use client';
/* ============================================================================
   Explainable AI — at-risk employees with the reasons behind each score.

   The model already knows *why* it flagged someone (feature importances +
   how far each value sits from the company baseline). This surfaces that,
   so an HR manager sees "3.6x the company absence rate" instead of a bare
   "73%" they have to take on faith.
   ========================================================================== */
import { useEffect, useState } from 'react';
import { Brain, ChevronDown, ChevronRight, ShieldCheck, AlertTriangle } from 'lucide-react';

interface Reason {
  feature: string;
  label: string;
  value: string;
  baseline: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
  deviation: number;
  importance: number;
  text: string;
}

interface RiskEmployee {
  employe_id: number;
  nom: string;
  probabilite: number;
  niveau: string;
  taux_absence: number;
  nb_absences: number;
  nb_retards: number;
  raisons?: Reason[];
  explication?: string;
}

const SEV_TONE: Record<string, string> = {
  high:   'badge-red',
  medium: 'badge-yellow',
  low:    'badge-gray',
};

export default function RiskPanel({ limit = 6 }: { limit?: number }) {
  const [rows, setRows]       = useState<RiskEmployee[] | null>(null);
  const [open, setOpen]       = useState<number | null>(null);
  const [failed, setFailed]   = useState(false);

  useEffect(() => {
    fetch('/api/ai/employes-a-risque')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setRows(Array.isArray(d) ? d : []))
      .catch(() => { setFailed(true); setRows([]); });
  }, []);

  return (
    <div className="card" style={{ marginBottom: 22 }}>
      <div className="card-head">
        <div>
          <div className="t-section" style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Brain size={15} style={{ color: 'var(--brand-400)' }} />
            Absenteeism risk — explained
          </div>
          <div className="t-meta" style={{ marginTop: 2 }}>
            Each score shows the factors the model actually weighted
          </div>
        </div>
        {rows && rows.length > 0 && (
          <span className="badge badge-blue">{rows.length} flagged</span>
        )}
      </div>

      {/* Loading */}
      {rows === null && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[0, 1, 2].map(i => <div key={i} className="skeleton" style={{ height: 48 }} />)}
        </div>
      )}

      {/* Empty / error */}
      {rows && rows.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            {failed ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
          </div>
          <div style={{ color: 'var(--gray-700)', fontWeight: 550, fontSize: '0.84rem' }}>
            {failed ? 'Risk data unavailable' : 'No employees currently at risk'}
          </div>
          <div className="t-meta" style={{ marginTop: 3, maxWidth: 340 }}>
            {failed
              ? 'The prediction service did not respond. Try regenerating alerts.'
              : 'Everyone is tracking close to the company baseline.'}
          </div>
        </div>
      )}

      {/* Rows */}
      {rows && rows.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {rows.slice(0, limit).map((e, i) => {
            const isOpen   = open === e.employe_id;
            const critical = e.niveau === 'Critique';
            const reasons  = e.raisons || [];
            return (
              <div
                key={e.employe_id}
                style={{ borderTop: i === 0 ? 'none' : '1px solid var(--border-subtle)' }}
              >
                <button
                  onClick={() => setOpen(isOpen ? null : e.employe_id)}
                  aria-expanded={isOpen}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 12,
                    background: 'none', border: 'none', cursor: 'pointer',
                    padding: '12px 2px', textAlign: 'left', fontFamily: 'var(--font-sans)',
                  }}
                >
                  <span style={{ color: 'var(--gray-400)', display: 'flex', flexShrink: 0 }}>
                    {isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                  </span>

                  <span style={{
                    flex: 1, minWidth: 0, color: 'var(--gray-900)',
                    fontSize: '0.84rem', fontWeight: 550,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {e.nom}
                  </span>

                  {/* risk bar */}
                  <span style={{ width: 92, flexShrink: 0 }} className="progress-track">
                    <span
                      className="progress-fill"
                      style={{
                        display: 'block',
                        width: `${Math.min(100, e.probabilite)}%`,
                        background: critical ? 'var(--danger)' : 'var(--warning)',
                      }}
                    />
                  </span>

                  <span className="t-num" style={{
                    width: 48, textAlign: 'right', flexShrink: 0,
                    fontSize: '0.84rem', fontWeight: 600,
                    color: critical ? 'var(--danger)' : 'var(--warning)',
                  }}>
                    {e.probabilite}%
                  </span>

                  <span className={critical ? 'badge badge-red' : 'badge badge-yellow'} style={{ flexShrink: 0 }}>
                    {critical ? 'Critical' : 'Medium'}
                  </span>
                </button>

                {isOpen && (
                  <div className="animate-fadein" style={{ padding: '2px 0 16px 27px' }}>
                    {reasons.length > 0 ? (
                      <>
                        <div className="t-label" style={{ marginBottom: 8 }}>Why this employee was flagged</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                          {reasons.map((r, j) => (
                            <div key={j} style={{ display: 'flex', alignItems: 'baseline', gap: 9 }}>
                              <span className={`badge ${SEV_TONE[r.severity] || 'badge-gray'}`} style={{ flexShrink: 0 }}>
                                {r.label}
                              </span>
                              <span className="t-body" style={{ fontSize: '0.8rem' }}>
                                <strong style={{ color: 'var(--gray-900)', fontWeight: 600 }}>{r.value}</strong>
                                {' '}vs {r.baseline} company average
                                <span className="t-meta"> · {r.detail}</span>
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="t-meta">
                        No single dominant factor — risk comes from a combination of weaker signals.
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: 18, marginTop: 12 }}>
                      <Metric label="Absence rate" value={`${e.taux_absence}%`} />
                      <Metric label="Absences"     value={e.nb_absences} />
                      <Metric label="Late arrivals" value={e.nb_retards} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="t-label">{label}</div>
      <div className="t-num" style={{ color: 'var(--gray-900)', fontSize: '0.88rem', fontWeight: 600, marginTop: 2 }}>
        {value}
      </div>
    </div>
  );
}
