import { BarChart3, BriefcaseBusiness, ChevronLeft, LayoutGrid, LogOut, Menu, PlusCircle, Settings, Ticket, X } from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

const navItems = [
  { label: 'Overview', path: '/overview', icon: LayoutGrid },
  { label: 'Tickets', path: '/tickets', icon: Ticket },
  { label: 'Create Ticket', path: '/tickets/new', icon: PlusCircle },
  { label: 'Analytics', path: '/analytics', icon: BarChart3 },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const nav = useNavigate();
  const location = useLocation();
  const sidebarRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSidebarOpen(false);
    };
    const onClick = (event: MouseEvent) => {
      if (!sidebarRef.current) return;
      if (sidebarOpen && !sidebarRef.current.contains(event.target as Node)) {
        setSidebarOpen(false);
      }
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [sidebarOpen]);

  function clearAuthState() {
    localStorage.removeItem('datastraw_session_token');
    localStorage.removeItem('datastraw_user_email');
    localStorage.removeItem('datastraw_login_email');
    localStorage.removeItem('datastraw_dev_otp');
  }

  async function handleLogout() {
    const token = localStorage.getItem('datastraw_session_token');
    try {
      if (token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } finally {
      clearAuthState();
      window.location.replace('/login');
    }
  }

  return (
    <div className="app-shell flex min-h-screen bg-warm text-slate-800">
      <aside
        ref={sidebarRef}
        className={`fixed inset-y-0 left-0 z-40 transform border-r border-slate-200 bg-white/95 p-5 shadow-lg transition-all duration-200 md:static md:translate-x-0 ${
          sidebarCollapsed ? 'md:w-20' : 'md:w-72'
        } ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className={`mb-8 flex items-center ${sidebarCollapsed ? 'justify-center' : 'justify-between'}`}>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
              <BriefcaseBusiness className="h-5 w-5" />
            </div>
            {!sidebarCollapsed ? <div>
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Support</div>
              <div className="text-lg font-semibold text-slate-800">CRM</div>
            </div> : null}
          </div>
          <div className="flex items-center gap-1">
            <button className="hidden rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:block" onClick={() => setSidebarCollapsed((value) => !value)} aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
              <ChevronLeft className={`h-5 w-5 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`} />
            </button>
            <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close navigation menu">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <nav className="space-y-2">
          {navItems.map(({ label, path, icon: Icon }) => {
            const active = location.pathname === path || (path === '/overview' && location.pathname === '/');
            return (
              <button
                key={path}
                onClick={() => nav(path)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium transition ${
                  active ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-100' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!sidebarCollapsed ? label : null}
              </button>
            );
          })}
        </nav>

        {!sidebarCollapsed ? <div className="mt-8 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
          <div className="font-semibold text-slate-700">Operations summary</div>
          <div className="mt-2 flex items-center justify-between">
            <span>Support load</span>
            <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">Healthy</span>
          </div>
        </div> : null}
        <button onClick={handleLogout} className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 ${sidebarCollapsed ? 'px-2' : ''}`} aria-label="Log out">
          <LogOut className="h-4 w-4" />
          {!sidebarCollapsed ? 'Logout' : null}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-8">
            <div className="flex items-center gap-3">
              <button className="rounded-lg border border-slate-200 p-2 text-slate-600 md:hidden" onClick={() => setSidebarOpen(true)} aria-label="Open navigation menu">
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Operations</p>
                <h1 className="text-xl font-semibold text-slate-800">Support CRM</h1>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-700">
                {localStorage.getItem('datastraw_user_email')?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="hidden text-right text-sm text-slate-600 md:block">
                <div className="font-medium text-slate-800">Support Desk</div>
                <div>{localStorage.getItem('datastraw_user_email') || 'user@datastraw.ai'}</div>
              </div>
              <button onClick={handleLogout} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50" aria-label="Log out">
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
