import { useCallback, useEffect, useRef, useState } from 'react'
import { AccountsPage } from './pages/AccountsPage'
import { CategoriesPage } from './pages/CategoriesPage'
import { DashboardPage } from './pages/DashboardPage'
import { TransactionsPage } from './pages/TransactionsPage'
import { AgendaPage } from './pages/AgendaPage'
import { CardsPage } from './pages/CardsPage'
import { ReportsPage } from './pages/ReportsPage'
import { ProfilePage } from './pages/ProfilePage'
import { getSupabase } from './auth/supabase'
import './App.css'
import './MobileSidebar.css'

const navigation = [
  { id: 'dashboard', label: 'Visão geral', icon: '⌂' }, { id: 'transactions', label: 'Transações', icon: '↔' },
  { id: 'agenda', label: 'Agenda', icon: '◷' }, { id: 'accounts', label: 'Contas', icon: '◫' },
  { id: 'cards', label: 'Cartões', icon: '▣' }, { id: 'reports', label: 'Relatórios', icon: '▤' },
  { id: 'categories', label: 'Categorias', icon: '◉' }, { id: 'profile', label: 'Perfil e segurança', icon: '♙' },
] as const
type Page = typeof navigation[number]['id']

function Brand() { return <div className="brand"><img className="brand-logo" src="/gicontrol-logo.png" alt="Logo da GiControl"/><div><strong>GiControl</strong><small>Gestão financeira</small></div></div> }

function App() {
  const [activePage, setActivePage] = useState<Page>('dashboard')
  const [connected, setConnected] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  const mobileSidebar = useRef<HTMLElement>(null)
  const handleConnectionChange = useCallback((value: boolean) => setConnected(value), [])
  const closeMenu = (restoreFocus = false) => { setMenuOpen(false); if (restoreFocus) window.setTimeout(() => menuButton.current?.focus(), 0) }
  const navigate = (page: Page) => { setActivePage(page); closeMenu(); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const signOut = () => void getSupabase().then((client) => client?.auth.signOut())

  useEffect(() => {
    if (!menuOpen) return
    const sidebar = mobileSidebar.current
    window.setTimeout(() => sidebar?.querySelector<HTMLElement>('[data-menu-focus]')?.focus(), 0)
    const handleKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setMenuOpen(false); window.setTimeout(() => menuButton.current?.focus(), 0); return }
      if (event.key !== 'Tab' || !sidebar) return
      const focusable = [...sidebar.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')]
      if (!focusable.length) return
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', handleKeyboard)
    return () => window.removeEventListener('keydown', handleKeyboard)
  }, [menuOpen])

  const nav = <nav aria-label="Navegação principal"><p className="nav-label">Menu</p>{navigation.map((item) => <button className={`nav-item ${activePage === item.id ? 'active' : ''}`} key={item.id} type="button" aria-current={activePage === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</nav>
  const footer = <div className="sidebar-footer"><div className={`connection-dot ${connected ? 'online' : ''}`}/><div><span>{connected ? 'API conectada' : 'API desconectada'}</span><small>Persistência segura</small></div><button className="sign-out" type="button" aria-label="Sair" onClick={signOut}>↪</button></div>

  return <div className="app-shell">
    <aside className="sidebar"><Brand/>{nav}{footer}</aside>
    <header className="mobile-app-header"><button ref={menuButton} className="menu-toggle" type="button" aria-label="Abrir menu" aria-expanded={menuOpen} aria-controls="mobile-sidebar" onClick={() => setMenuOpen(true)}>☰</button><img src="/gicontrol-logo.png" alt=""/><strong>GiControl</strong></header>
    <div className={`mobile-sidebar-backdrop ${menuOpen ? 'open' : ''}`} aria-hidden={!menuOpen} onMouseDown={(event) => event.target === event.currentTarget && closeMenu(true)}>
      <aside ref={mobileSidebar} id="mobile-sidebar" className="mobile-sidebar" role="dialog" aria-modal="true" aria-label="Menu móvel"><div className="mobile-sidebar-heading"><Brand/><button data-menu-focus type="button" aria-label="Fechar menu" onClick={() => closeMenu(true)}>×</button></div>{nav}{footer}</aside>
    </div>
    <main>{activePage === 'accounts' ? <AccountsPage/> : activePage === 'cards' ? <CardsPage/> : activePage === 'reports' ? <ReportsPage/> : activePage === 'transactions' ? <TransactionsPage/> : activePage === 'agenda' ? <AgendaPage/> : activePage === 'categories' ? <CategoriesPage/> : activePage === 'profile' ? <ProfilePage/> : <DashboardPage onConnectionChange={handleConnectionChange}/>}</main>
  </div>
}
export default App
