'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import EmployeeSidebar from '../components/EmployeeSidebar';
import TopBar from '../components/TopBar';

export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [navOpen, setNavOpen] = useState(false);   // mobile drawer

  // Close the drawer on navigation, otherwise it stays over the new page.
  useEffect(() => { setNavOpen(false); }, [pathname]);

  useEffect(() => {
    const raw = localStorage.getItem('inet_user');
    if (!raw) { router.push('/'); return; }
    try {
      const parsed = JSON.parse(raw);
      if (!parsed?.employe?.employe_id) { router.push('/'); return; }
    } catch { router.push('/'); return; }
    setReady(true);
  }, []);

  if (!ready) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent' }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ margin: '0 auto 12px' }} />
        <div style={{ color: '#6B879B', fontSize: '0.82rem', fontWeight: 500 }}>Loading...</div>
      </div>
    </div>
  );

  return (
    <div className={`app-shell${navOpen ? ' nav-open' : ''}`} style={{ display: 'flex', minHeight: '100vh', background: 'transparent' }}>
      <EmployeeSidebar />
      <div className="nav-scrim" onClick={() => setNavOpen(false)} aria-hidden />
      <div className="app-main" style={{ ['--sidebar-w' as string]: '240px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh', minWidth: 0 }}>
        <TopBar onMenu={() => setNavOpen(v => !v)} />
        <main key={pathname} className="view-enter" style={{ flex: 1, padding: '28px 32px', minWidth: 0 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
