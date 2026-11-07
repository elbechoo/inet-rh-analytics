'use client';
/* iNET brand mark - the real one:
   a solid azure square, "iNET" set in white, with the leading "i" in deep navy. */

export function LogoMark({ size = 40, radius = 8 }: { size?: number; radius?: number }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: radius, flexShrink: 0,
      background: 'var(--sky-500)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      lineHeight: 1, letterSpacing: '-.04em',
    }}>
      <span style={{ fontWeight: 800, fontSize: size * 0.42, color: 'var(--navy-700)' }}>i</span>
      <span style={{ fontWeight: 800, fontSize: size * 0.42, color: '#fff' }}>N</span>
    </div>
  );
}

export function LogoWordmark({
  size = 40, subtitle = 'Système de Gestion RH Intelligente', dark = false, collapsed = false,
}: { size?: number; subtitle?: string | null; dark?: boolean; collapsed?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11, minWidth: 0 }}>
      <LogoMark size={size} />
      {!collapsed && (
        <div style={{ minWidth: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'baseline', gap: 6,
            fontWeight: 800, fontSize: size * 0.46, letterSpacing: '-.035em', lineHeight: 1.1,
          }}>
            <span>
              <span style={{ color: dark ? 'var(--sky-400)' : 'var(--navy-700)' }}>i</span>
              <span style={{ color: dark ? '#fff' : 'var(--ink)' }}>NET</span>
            </span>
            <span style={{
              background: 'var(--sky-500)', color: '#fff',
              fontSize: size * 0.24, fontWeight: 800, letterSpacing: '.06em',
              padding: '3px 7px', borderRadius: 5,
            }}>RH</span>
          </div>
          {subtitle && (
            <div style={{
              fontSize: size * 0.2, marginTop: 2, whiteSpace: 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis',
              color: dark ? 'rgba(226,240,250,.55)' : 'var(--muted)',
            }}>{subtitle}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default LogoWordmark;
