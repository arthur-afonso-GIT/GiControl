import { useCallback, useEffect, useState } from 'react'
import { AccountsPage } from './pages/AccountsPage'
import { CategoriesPage } from './pages/CategoriesPage'
import { DashboardPage } from './pages/DashboardPage'
import { TransactionsPage } from './pages/TransactionsPage'
import { AgendaPage } from './pages/AgendaPage'
import { CardsPage } from './pages/CardsPage'
import { ReportsPage } from './pages/ReportsPage'
import './App.css'
import { getSupabase } from './auth/supabase'

const navigation = [
  { id: 'dashboard', label: 'Visão geral', icon: '⌂' },
  { id: 'transactions', label: 'Transações', icon: '↔' },
  { id: 'agenda', label: 'Agenda', icon: '◷' },
  { id: 'accounts', label: 'Contas', icon: '◫' },
  { id: 'cards', label: 'Cartões', icon: '▣' },
  { id: 'reports', label: 'Relatórios', icon: '▤' },
  { id: 'categories', label: 'Categorias', icon: '◉' },
] as const
type Page = typeof navigation[number]['id']

function App() {
  const [activePage, setActivePage] = useState<Page>('dashboard')
  const [connected, setConnected] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const handleConnectionChange = useCallback((value: boolean) => setConnected(value), [])
  const navigate = (page: Page) => { setActivePage(page); setMoreOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  useEffect(() => {
    const closeWithEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setMoreOpen(false) }
    window.addEventListener('keydown', closeWithEscape)
    return () => window.removeEventListener('keydown', closeWithEscape)
  }, [])

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><img className="brand-logo" src="/gicontrol-logo.png" alt="Logo da GiControl" /><div><strong>GiControl</strong><small>Gestão financeira</small></div></div>
      <nav aria-label="Navegação principal"><p className="nav-label">Menu</p>{navigation.map((item) => <button className={`nav-item ${activePage === item.id ? 'active' : ''}`} key={item.id} type="button" onClick={() => navigate(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</nav>
      <div className="sidebar-footer"><div className={`connection-dot ${connected ? 'online' : ''}`} /><div><span>{connected ? 'API conectada' : 'API desconectada'}</span><small>Persistência segura</small></div><button className="sign-out" type="button" aria-label="Sair" onClick={() => void getSupabase().then((client) => client?.auth.signOut())}>↪</button></div>
    </aside>
    <main>{activePage === 'accounts' ? <AccountsPage /> : activePage === 'cards' ? <CardsPage /> : activePage === 'reports' ? <ReportsPage /> : activePage === 'transactions' ? <TransactionsPage /> : activePage === 'agenda' ? <AgendaPage /> : activePage === 'categories' ? <CategoriesPage /> : <DashboardPage onConnectionChange={handleConnectionChange} />}</main>
    <nav className="mobile-navigation" aria-label="Navegação móvel">
      <MobileNavButton active={activePage === 'dashboard'} icon="⌂" label="Início" onClick={() => navigate('dashboard')} />
      <MobileNavButton active={activePage === 'agenda'} icon="◷" label="Agenda" onClick={() => navigate('agenda')} />
      <button className="mobile-create" type="button" aria-label="Adicionar transação" onClick={() => navigate('transactions')}><span aria-hidden="true">＋</span></button>
      <MobileNavButton active={activePage === 'transactions'} icon="↔" label="Transações" onClick={() => navigate('transactions')} />
      <MobileNavButton active={moreOpen || activePage === 'accounts' || activePage === 'cards' || activePage === 'reports' || activePage === 'categories'} icon="•••" label="Mais" expanded={moreOpen} onClick={() => setMoreOpen((value) => !value)} />
    </nav>
    {moreOpen && <div className="mobile-more-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setMoreOpen(false)}><section className="mobile-more-sheet" role="dialog" aria-modal="true" aria-label="Mais opções"><div className="mobile-sheet-handle" /><strong>Mais opções</strong><button type="button" onClick={() => navigate('accounts')}><span aria-hidden="true">◫</span><div>Contas<small>Saldos e recebimentos mensais</small></div></button><button type="button" onClick={() => navigate('cards')}><span aria-hidden="true">▣</span><div>Cartões<small>Limites, compras e faturas</small></div></button><button type="button" onClick={() => navigate('reports')}><span aria-hidden="true">▤</span><div>Relatórios<small>Fechamento e exportação mensal</small></div></button><button type="button" onClick={() => navigate('categories')}><span aria-hidden="true">◉</span><div>Categorias<small>Organização e limites mensais</small></div></button><button type="button" onClick={() => void getSupabase().then((client) => client?.auth.signOut())}><span aria-hidden="true">↪</span><div>Sair<small>Encerrar a sessão neste aparelho</small></div></button><button className="mobile-sheet-close" type="button" onClick={() => setMoreOpen(false)}>Fechar</button></section></div>}
  </div>
}

function MobileNavButton({ active, icon, label, expanded, onClick }: { active: boolean; icon: string; label: string; expanded?: boolean; onClick: () => void }) {
  return <button className={active ? 'active' : ''} type="button" aria-current={active ? 'page' : undefined} aria-expanded={expanded} onClick={onClick}><span aria-hidden="true">{icon}</span><small>{label}</small></button>
}

export default App
