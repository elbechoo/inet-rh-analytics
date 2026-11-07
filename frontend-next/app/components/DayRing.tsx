'use client';
/* The day as one rotation.
   07:00 sits at the top and the day sweeps clockwise to 19:00. The bright arc
   is elapsed time, the puck is now, and every dot is one arrival placed at its
   clock angle - pushed inward the later it was. The core repeats the logo:
   light periwinkle disc, white figure. */
import { useEffect, useMemo, useRef, useState } from 'react';

export interface Arrival { late: number; hour: number }

interface Props {
  present: number;
  total: number;
  arrivals?: Arrival[];
  departments?: { name: string; count: number }[];
  dayStart?: number;
  dayEnd?: number;
  size?: number;
}

const TINTS = ['#DDF1FB', '#7FCFF0', '#45B9E9', '#0FA3E0', '#0B87BE'];

export default function DayRing({
  present, total, arrivals = [], departments = [],
  dayStart = 7, dayEnd = 19, size = 560,
}: Props) {
  const [t, setT] = useState(0);              // 0->1 entrance progress
  const [scrub, setScrub] = useState<number | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const span = dayEnd - dayStart;
  const C = size / 2;
  const R = size / 2 - 40;
  const TRACK = 22;

  // live clock position, or the scrubbed one
  const nowH = useMemo(() => {
    const d = new Date();
    return d.getHours() + d.getMinutes() / 60;
  }, []);
  const elapsed = scrub ?? Math.min(Math.max(nowH - dayStart, 0), span);

  useEffect(() => {
    let raf = 0; const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - t0) / 900, 1);
      setT(1 - Math.pow(1 - p, 3));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const ang = (h: number) => (-Math.PI / 2) + (h / span) * Math.PI * 2;
  const pt = (h: number, r: number) => ({ x: C + Math.cos(ang(h)) * r, y: C + Math.sin(ang(h)) * r });

  // donut arc path
  const arcPath = (from: number, to: number, rOuter: number, w: number) => {
    const rIn = rOuter - w;
    const a0 = ang(from), a1 = ang(to);
    const large = (a1 - a0) > Math.PI ? 1 : 0;
    const p0 = { x: C + Math.cos(a0) * rOuter, y: C + Math.sin(a0) * rOuter };
    const p1 = { x: C + Math.cos(a1) * rOuter, y: C + Math.sin(a1) * rOuter };
    const p2 = { x: C + Math.cos(a1) * rIn,    y: C + Math.sin(a1) * rIn };
    const p3 = { x: C + Math.cos(a0) * rIn,    y: C + Math.sin(a0) * rIn };
    return `M${p0.x} ${p0.y} A${rOuter} ${rOuter} 0 ${large} 1 ${p1.x} ${p1.y} L${p2.x} ${p2.y} A${rIn} ${rIn} 0 ${large} 0 ${p3.x} ${p3.y} Z`;
  };

  function onMove(e: React.MouseEvent) {
    if (!wrapRef.current) return;
    const r = wrapRef.current.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2);
    const dy = e.clientY - (r.top + r.height / 2);
    const dist = Math.hypot(dx, dy);
    if (dist < R * 0.6 || dist > R * 1.25) return;      // only on the ring band
    let a = Math.atan2(dy, dx) + Math.PI / 2;
    if (a < 0) a += Math.PI * 2;
    setScrub((a / (Math.PI * 2)) * span);
  }

  const shown = elapsed * t;
  const puck = pt(shown, R - TRACK / 2);
  const pct = total ? Math.round((present / total) * 100) : 0;
  const label = `${String(Math.floor(dayStart + elapsed)).padStart(2, '0')}:${String(Math.round(((dayStart + elapsed) % 1) * 60)).padStart(2, '0')}`;

  let acc = 0;
  const totalDept = departments.reduce((s, d) => s + d.count, 0) || 1;

  return (
    <div
      ref={wrapRef}
      onMouseMove={onMove}
      onMouseLeave={() => setScrub(null)}
      style={{ width: size, height: size, position: 'relative', cursor: 'crosshair', userSelect: 'none' }}
    >
      <svg width={size} height={size} style={{ display: 'block', overflow: 'visible' }}>
        <defs>
          <linearGradient id="dayGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#0FA3E0" />
            <stop offset="55%"  stopColor="#45B9E9" />
            <stop offset="100%" stopColor="#DDF1FB" />
          </linearGradient>
          <radialGradient id="coreGrad" cx="30%" cy="25%">
            <stop offset="0%"   stopColor="#7FCFF0" />
            <stop offset="100%" stopColor="#0B87BE" />
          </radialGradient>
          <filter id="coreGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="18" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* day track */}
        <path d={arcPath(0, span - 0.001, R, TRACK)} fill="#1E255C" />

        {/* elapsed */}
        {shown > 0.02 && <path d={arcPath(0, shown, R, TRACK)} fill="url(#dayGrad)" />}

        {/* hour ticks */}
        {Array.from({ length: span }, (_, h) => {
          const major = h % 3 === 0;
          const a = pt(h, R + 12), b = pt(h, R + (major ? 22 : 17));
          return <line key={h} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                       stroke={major ? '#39408A' : '#262D6B'} strokeWidth={major ? 2 : 1.5} strokeLinecap="round" />;
        })}
        {Array.from({ length: span }, (_, h) => h).filter(h => h % 3 === 0).map(h => {
          const p = pt(h, R + 38);
          return <text key={h} x={p.x} y={p.y} fill="#6E79C4" fontSize="10.5" fontWeight="500"
                       textAnchor="middle" dominantBaseline="middle">
            {String(dayStart + h).padStart(2, '0')}:00
          </text>;
        })}

        {/* department ring */}
        {departments.map((d, i) => {
          const from = (acc / totalDept) * span;
          acc += d.count;
          const to = (acc / totalDept) * span - 0.08;
          return <path key={d.name} d={arcPath(from, Math.max(to, from + 0.05), R - 34, 11)}
                       fill={TINTS[i % TINTS.length]} opacity={0.9 * t} />;
        })}

        {/* arrivals */}
        {arrivals.map((a, i) => {
          const rr = R - 58 - Math.min(a.late, 100) * 0.34;
          const p = pt(Math.min(Math.max(a.hour - dayStart, 0), span), rr);
          const col = a.late <= 0 ? '#FFFFFF' : a.late < 30 ? '#7FCFF0' : '#DDF1FB';
          return <circle key={i} cx={p.x} cy={p.y} r={a.late <= 0 ? 3 : 3.6}
                         fill={col} opacity={(a.late <= 0 ? 0.9 : 1) * t} />;
        })}

        {/* now puck */}
        {shown > 0.02 && (
          <>
            <circle cx={puck.x} cy={puck.y} r={20} fill="#45B9E9" opacity={0.28} />
            <circle cx={puck.x} cy={puck.y} r={8} fill="#FFFFFF" stroke="#45B9E9" strokeWidth={4} />
          </>
        )}

        {/* core */}
        <circle cx={C} cy={C} r={R - 90} fill="url(#coreGrad)" filter="url(#coreGlow)" />
        <circle cx={C} cy={C} r={R - 104} fill="none" stroke="#FFFFFF" strokeOpacity={0.3} strokeWidth={1.5} />
      </svg>

      {/* core readout - white type on the light disc, exactly like the mark */}
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
      }}>
        <div style={{ fontSize: '.63rem', fontWeight: 700, letterSpacing: '.16em', color: 'rgba(255,255,255,.75)' }}>
          CHECKED IN
        </div>
        <div className="t-num" style={{
          fontSize: '3.6rem', fontWeight: 700, color: '#fff', lineHeight: 1.05, letterSpacing: '-.04em',
        }}>
          {present}
        </div>
        <div style={{ fontSize: '.8rem', fontWeight: 600, color: 'rgba(255,255,255,.9)' }}>
          of {total} · {pct}%
        </div>
        <div style={{ fontSize: '.7rem', color: 'rgba(255,255,255,.65)', marginTop: 2 }}>
          {scrub !== null ? `replay ${label}` : label}
        </div>
      </div>
    </div>
  );
}
