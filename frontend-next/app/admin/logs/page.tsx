'use client';
import { useEffect, useState, useRef } from 'react';
import { RefreshCw, ScrollText } from 'lucide-react';
import { authFetch } from '@/app/lib/api';

const SOURCES = ['all', 'etl', 'scheduler', 'email'];

const levelStyle = (msg: string) => {
  const m = msg.toLowerCase();
  if (m.includes('error') || m.includes('fail'))    return { dot: '#f85149', text: '#fca5a5' };
  if (m.includes('warn'))                            return { dot: '#e3b341', text: '#fcd34d' };
  if (m.includes('success') || m.includes('ok'))    return { dot: '#3fb950', text: '#6ee7b7' };
  return { dot: '#45B9E9', text: '#34546A' };
};

export default function AdminLogs() {
  const [logs,        setLogs]        = useState<any[]>([]);
  const [source,      setSource]      = useState('all');
  const [search,      setSearch]      = useState('');
  const [loading,     setLoading]     = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<any>(null);

  const load = (src = source) => {
    const url = src === 'all' ? '/api/admin/logs' : `/api/admin/logs?source=${src}`;
    authFetch(url)
      .then(r => r.json())
      .then(d => { setLogs(Array.isArray(d) ? d : []); setLoading(false); })
      .catch(() => { setLogs([]); setLoading(false); });
  };

  useEffect(() => { load(source); }, [source]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => load(source), 5000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [autoRefresh, source]);

  const filtered = logs.filter(l =>
    l.message?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0C2436', margin: 0, letterSpacing: '-0.3px' }}>System Logs</h1>
          <p style={{ color: '#6B879B', marginTop: 4, fontSize: '0.82rem' }}>{filtered.length} entries</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.80rem', color: '#6B879B', cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}
              style={{ accentColor: '#0FA3E0', width: 14, height: 14 }} />
            Auto-refresh (5s)
          </label>
          <button onClick={() => load(source)} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '9px 16px', borderRadius: 9, border: '1px solid var(--border)',
            background: 'var(--surface)', color: '#34546A', fontSize: '0.82rem', cursor: 'pointer',
            fontFamily: 'Inter, sans-serif',
          }}>
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <input
          placeholder="Search logs..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, padding: '10px 16px', borderRadius: 10, border: '1px solid var(--border)', fontSize: '0.82rem', fontFamily: 'monospace', outline: 'none', background: 'rgba(12,36,54,0.04)', color: '#0C2436' }}
          onFocus={e => (e.currentTarget.style.borderColor = '#0FA3E0')}
          onBlur={e => (e.currentTarget.style.borderColor = 'rgba(12,36,54,0.04)')}
        />
        {SOURCES.map(s => (
          <button key={s} onClick={() => setSource(s)} style={{
            padding: '10px 18px', borderRadius: 10, border: '1.5px solid',
            borderColor: source === s ? '#0FA3E0' : 'rgba(12,36,54,0.04)',
            background: source === s ? 'rgba(15,163,224,0.15)' : 'rgba(12,36,54,0.04)',
            color: source === s ? '#45B9E9' : '#6B879B',
            fontWeight: source === s ? 700 : 500, fontSize: '0.82rem', cursor: 'pointer',
            textTransform: 'capitalize', fontFamily: 'Inter, sans-serif',
          }}>
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>

      {/* Log terminal */}
      <div style={{ background: '#F2F7FB', borderRadius: 'var(--radius-lg)', padding: 20, minHeight: 420, maxHeight: 620, overflowY: 'auto', border: '1px solid var(--border)', boxShadow: '0 4px 24px rgba(0,0,0,0.3)' }}>
        {/* Terminal header bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid rgba(12,36,54,0.04)' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f85149' }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#e3b341' }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#3fb950' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 8 }}>
            <ScrollText size={12} color="#9DB3C2" />
            <span style={{ fontSize: '0.72rem', color: '#9DB3C2', fontFamily: 'monospace' }}>iNET RH - system logs</span>
          </div>
        </div>

        {loading ? (
          <div style={{ color: '#45B9E9', textAlign: 'center', padding: 40, fontSize: '0.84rem', fontFamily: 'monospace' }}>Loading logs...</div>
        ) : filtered.length === 0 ? (
          <div style={{ color: '#9DB3C2', textAlign: 'center', padding: 40, fontSize: '0.82rem', fontFamily: 'monospace' }}>
            No logs found. Make sure the .log files exist in the project directory.
          </div>
        ) : (
          filtered.map((log, i) => {
            const { dot, text } = levelStyle(log.message);
            return (
              <div key={i} style={{
                display: 'flex', gap: 10, alignItems: 'flex-start',
                padding: '6px 10px', borderRadius: 6, marginBottom: 2,
                borderLeft: `3px solid ${dot}`,
                background: 'rgba(12,36,54,0.04)',
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: dot, marginTop: 7, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <span style={{ color: '#9DB3C2', fontSize: '0.70rem', fontFamily: 'monospace', marginRight: 10 }}>
                    [{log.source}]
                  </span>
                  <span style={{ color: text, fontSize: '0.78rem', fontFamily: 'monospace' }}>
                    {log.message}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div style={{ marginTop: 10, fontSize: '0.72rem', color: '#9DB3C2' }}>
        Logs are read from <code style={{ background: 'rgba(12,36,54,0.04)', padding: '1px 5px', borderRadius: 4, color: '#6B879B' }}>.log</code> files in the project directory. Run the scheduler or ETL first if logs are empty.
      </div>
    </div>
  );
}
