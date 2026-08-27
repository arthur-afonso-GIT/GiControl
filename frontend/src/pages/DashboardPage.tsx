import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AgendaSummary, CategoryBudget, DashboardMetrics, ExpenseOccurrence, ScheduledIncome } from '../api/types'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const currentMonth = () => { const value = new Date(); return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}` }

export function DashboardPage({ onConnectionChange }: { onConnectionChange: (connected: boolean) => void }) {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [budgets, setBudgets] = useState<CategoryBudget[]>([])
  const [scheduledIncomes, setScheduledIncomes] = useState<ScheduledIncome[]>([])
  const [agenda, setAgenda] = useState<AgendaSummary | null>(null)
  const [expenses, setExpenses] = useState<ExpenseOccurrence[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [month, setMonth] = useState(currentMonth)

  const loadDashboard = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [health, dashboard, budgetData, incomeData, agendaData, expenseData] = await Promise.all([api.health(), api.dashboard(month), api.budgets(month), api.scheduledIncomes.list(month), api.agendaSummary(month), api.recurringExpenses.occurrences(month)])
      onConnectionChange(health.status === 'ok'); setMetrics(dashboard); setBudgets(budgetData); setScheduledIncomes(incomeData); setAgenda(agendaData); setExpenses(expenseData)
    } catch (requestError) {
      onConnectionChange(false)
      setError(requestError instanceof Error ? requestError.message : 'Não foi possível carregar seus dados.')
    } finally { setLoading(false) }
  }, [month, onConnectionChange])

  // oxlint-disable-next-line react/set-state-in-effect -- sincroniza o painel com a API ao montar e trocar o mês.
  useEffect(() => { void loadDashboard() }, [loadDashboard])

  async function confirmIncome(item: ScheduledIncome) {
    setLoading(true); setError(null)
    try { await api.scheduledIncomes.confirm(item.account_id, month); await loadDashboard() }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível confirmar a renda.') }
    finally { setLoading(false) }
  }

  return <>
    <header className="topbar dashboard-header"><div><p className="eyebrow">PAINEL FINANCEIRO</p><h1>Visão geral</h1><p className="subtitle">Acompanhe o que importa, sem perder o controle.</p></div><div className="dashboard-actions"><label>Mês<input type="month" value={month} onChange={(event) => setMonth(event.target.value || currentMonth())} /></label><button className="refresh-button" type="button" onClick={() => void loadDashboard()}><span aria-hidden="true">↻</span>Atualizar</button></div></header>
    {error && <section className="error-state" role="alert"><div><strong>Não foi possível conectar à API</strong><p>{error} Confirme que o FastAPI está rodando na porta 8000.</p></div><button type="button" onClick={() => void loadDashboard()}>Tentar novamente</button></section>}
    {agenda && agenda.overdue_count > 0 && <section className="agenda-alert" role="alert"><span aria-hidden="true">!</span><div><strong>{agenda.overdue_count} {agenda.overdue_count === 1 ? 'conta vencida' : 'contas vencidas'}</strong><p>Confira a Agenda para confirmar, adiar ou cancelar a ocorrência.</p></div></section>}
    <section className="metric-grid" aria-label="Resumo financeiro"><MetricCard label="Saldo total" value={metrics?.current_balance} loading={loading} tone="indigo" symbol="◆" /><MetricCard label="Receitas do mês" value={metrics?.monthly_income} loading={loading} tone="green" symbol="↗" /><MetricCard label="Despesas do mês" value={metrics?.monthly_expense} loading={loading} tone="orange" symbol="↘" /><MetricCard label="Saldo projetado" value={agenda?.projected_balance} loading={loading} tone="violet" symbol="◎" /></section>
    <section className="content-grid">
      <article className="panel recent-panel"><div className="panel-heading"><div><p className="eyebrow">MOVIMENTAÇÕES</p><h2>Transações recentes</h2></div><span className="count-badge">{metrics?.recent_transactions.length ?? 0}</span></div>{loading ? <div className="transaction-list skeleton-list" aria-label="Carregando transações"><i /><i /><i /></div> : metrics?.recent_transactions.length ? <div className="transaction-list">{metrics.recent_transactions.map((transaction) => <div className="transaction-row" key={transaction.id}><span className={`transaction-icon ${transaction.type === 'Receita' ? 'income' : 'expense'}`}>{transaction.type === 'Receita' ? '↗' : '↘'}</span><div className="transaction-copy"><strong>{transaction.description}</strong><span>{formatDate(transaction.date)} · {transaction.type}</span></div><strong className={transaction.type === 'Receita' ? 'positive' : 'negative'}>{transaction.type === 'Receita' ? '+' : '−'} {currency.format(transaction.amount)}</strong></div>)}</div> : <div className="empty-state"><span>↔</span><strong>Nenhuma transação ainda</strong><p>Seus lançamentos mais recentes aparecerão aqui.</p></div>}</article>
      <article className="panel health-panel"><p className="eyebrow">SAÚDE FINANCEIRA</p><h2>Resumo do mês</h2><div className="health-visual"><HealthRing rate={calculateSavingsRate(metrics)} /></div><div className="health-legend"><span><i className="legend-income" /> Receitas</span><span><i className="legend-expense" /> Despesas</span></div></article>
    </section>
    <section className="panel budget-panel"><div className="panel-heading"><div><p className="eyebrow">ORÇAMENTO DO MÊS</p><h2>Limites por categoria</h2></div><span className="count-badge">{budgets.length}</span></div>{budgets.length ? <div className="budget-list">{budgets.map((budget) => <div className={`budget-row ${budget.usage_percentage > 100 ? 'over' : ''}`} key={budget.category_id}><div className="budget-copy"><strong>{budget.category_name}</strong><span>{currency.format(budget.spent)} de {currency.format(budget.limit)}</span></div><div className="budget-progress"><i><span style={{ width: `${Math.min(100, budget.usage_percentage)}%` }} /></i><b>{Math.round(budget.usage_percentage)}%</b></div><small>{budget.remaining >= 0 ? `${currency.format(budget.remaining)} disponíveis` : `${currency.format(Math.abs(budget.remaining))} acima do limite`}</small></div>)}</div> : <div className="budget-empty"><strong>Nenhum limite configurado</strong><p>Defina limites nas categorias de despesa para acompanhar seu orçamento.</p></div>}</section>
    {scheduledIncomes.length > 0 && <section className="panel scheduled-panel"><div className="panel-heading"><div><p className="eyebrow">RECEBIMENTOS</p><h2>Rendas previstas</h2></div><span className="count-badge">{scheduledIncomes.length}</span></div><div className="scheduled-list">{scheduledIncomes.map((item) => { const canConfirm = item.due_date <= new Date().toISOString().slice(0, 10); return <div className="scheduled-row" key={item.account_id}><div><strong>{item.account_name}</strong><span>Previsto para {formatFullDate(item.due_date)}</span></div><b>{currency.format(item.amount)}</b>{item.confirmed ? <span className="scheduled-status confirmed">Recebido</span> : canConfirm ? <button className="primary-button" disabled={loading} type="button" onClick={() => void confirmIncome(item)}>Confirmar recebimento</button> : <span className="scheduled-status">Previsto</span>}</div>})}</div></section>}
    {expenses.length > 0 && <section className="panel scheduled-panel"><div className="panel-heading"><div><p className="eyebrow">PRÓXIMOS COMPROMISSOS</p><h2>Despesas previstas</h2></div><span className="count-badge">{expenses.filter((item) => !item.confirmed).length}</span></div><div className="scheduled-list">{expenses.filter((item) => !item.confirmed).slice(0, 5).map((item) => <div className="scheduled-row" key={item.id}><div><strong>{item.name}</strong><span>Vence em {formatFullDate(item.due_date)}</span></div><b className="negative">− {currency.format(item.amount)}</b><span className={`scheduled-status ${item.due_date < new Date().toISOString().slice(0, 10) ? 'overdue' : ''}`}>{item.due_date < new Date().toISOString().slice(0, 10) ? 'Vencida' : 'Prevista'}</span></div>)}</div></section>}
  </>
}

type MetricCardProps = { label: string; value?: number; loading: boolean; tone: 'indigo' | 'green' | 'orange' | 'violet'; symbol: string }
function MetricCard({ label, value, loading, tone, symbol }: MetricCardProps) { return <article className={`metric-card ${tone}`}><div className="metric-topline"><span className="metric-symbol" aria-hidden="true">{symbol}</span><span className="metric-period">Mês selecionado</span></div><p>{label}</p>{loading ? <i className="metric-skeleton" /> : <strong>{currency.format(value ?? 0)}</strong>}</article> }
function HealthRing({ rate }: { rate: number }) { const boundedRate = Math.min(100, rate); return <div className="health-ring" style={{ background: `radial-gradient(circle at center, #fff 58%, transparent 59%), conic-gradient(#ec4899 0 ${boundedRate}%, #f3e8ff ${boundedRate}% 100%)` }}><span>{rate}%</span><small>economizado</small></div> }
function formatDate(value: string) { return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(new Date(`${value}T12:00:00`)) }
function formatFullDate(value: string) { return new Intl.DateTimeFormat('pt-BR').format(new Date(`${value}T12:00:00`)) }
function calculateSavingsRate(metrics: DashboardMetrics | null) { if (!metrics || metrics.monthly_income <= 0) return 0; return Math.max(0, Math.round((metrics.savings / metrics.monthly_income) * 100)) }
