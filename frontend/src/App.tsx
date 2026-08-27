import { useCallback, useState } from 'react'
import { AccountsPage } from './pages/AccountsPage'
import { CategoriesPage } from './pages/CategoriesPage'
import { DashboardPage } from './pages/DashboardPage'
import { TransactionsPage } from './pages/TransactionsPage'
import './App.css'

const navigation = [
  { id: 'dashboard', label: 'Visão geral', icon: '⌂' },
  { id: 'transactions', label: 'Transações', icon: '↔' },
  { id: 'accounts', label: 'Contas', icon: '◫' },
  { id: 'categories', label: 'Categorias', icon: '◉' },
] as const
type Page = typeof navigation[number]['id']

function App() {
  const [activePage, setActivePage] = useState<Page>('dashboard')
  const [connected, setConnected] = useState(false)
  const handleConnectionChange = useCallback((value: boolean) => setConnected(value), [])

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">F</span><div><strong>Fincontrol</strong><small>Gestão financeira</small></div></div>
      <nav aria-label="Navegação principal"><p className="nav-label">Menu</p>{navigation.map((item) => <button className={`nav-item ${activePage === item.id ? 'active' : ''}`} key={item.id} type="button" onClick={() => setActivePage(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</nav>
      <div className="sidebar-footer"><div className={`connection-dot ${connected ? 'online' : ''}`} /><div><span>{connected ? 'API conectada' : 'API desconectada'}</span><small>Persistência SQLite</small></div></div>
    </aside>
    <main>{activePage === 'accounts' ? <AccountsPage /> : activePage === 'transactions' ? <TransactionsPage /> : activePage === 'categories' ? <CategoriesPage /> : <DashboardPage onConnectionChange={handleConnectionChange} />}</main>
  </div>
}

export default App
