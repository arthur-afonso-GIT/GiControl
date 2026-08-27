import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Account, Category, Transaction, TransactionCreate, TransactionType } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { buildExpenseForecast } from '../features/transactions/forecast'
import './TransactionsPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const today = () => { const value = new Date(); return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}` }
const emptyTransaction = (): TransactionCreate => ({ amount: 0, date: today(), category_id: '', account_id: '', description: '', type: 'Despesa', installments: 1, is_fixed: false })

export function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [initialForm, setInitialForm] = useState<TransactionCreate | null>(null)
  const [confirmExit, setConfirmExit] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<Transaction | null>(null)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [form, setForm] = useState<TransactionCreate>(emptyTransaction)
  const [month, setMonth] = useState(today().slice(0, 7))
  const [type, setType] = useState<'Todos' | TransactionType>('Todos')
  const [accountFilter, setAccountFilter] = useState('Todos')

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [transactionData, accountData, categoryData] = await Promise.all([api.transactions.list(), api.accounts.list(), api.categories.list()])
      setTransactions(transactionData); setAccounts(accountData); setCategories(categoryData)
    } catch (requestError) { setError(messageFrom(requestError)) }
    finally { setLoading(false) }
  }, [])

  // oxlint-disable-next-line react/set-state-in-effect -- sincroniza a página com a API ao montar.
  useEffect(() => { void load() }, [load])

  const filtered = useMemo(() => transactions.filter((transaction) =>
    (!month || transaction.date.startsWith(month)) &&
    (type === 'Todos' || transaction.type === type) &&
    (accountFilter === 'Todos' || transaction.account_id === accountFilter)
  ).sort((a, b) => b.date.localeCompare(a.date)), [transactions, month, type, accountFilter])

  const income = filtered.filter((item) => item.type === 'Receita').reduce((sum, item) => sum + item.amount, 0)
  const expense = filtered.filter((item) => item.type === 'Despesa').reduce((sum, item) => sum + item.amount, 0)
  const availableCategories = categories.filter((category) => category.type === form.type)
  const forecast = useMemo(() => buildExpenseForecast(transactions, accounts, today().slice(0, 7)), [transactions, accounts])
  const formIsDirty = initialForm !== null && JSON.stringify(form) !== JSON.stringify(initialForm)

  function openCreate() {
    const next = emptyTransaction()
    next.account_id = accounts[0]?.id ?? ''
    next.category_id = categories.find((category) => category.type === next.type)?.id ?? ''
    setEditing(null); setForm(next); setInitialForm(next); setDrawerOpen(true)
  }

  function openEdit(transaction: Transaction) {
    const next: TransactionCreate = { amount: transaction.amount, date: transaction.date, category_id: transaction.category_id, account_id: transaction.account_id, description: transaction.description, type: transaction.type, installments: 1, is_fixed: transaction.is_fixed }
    setEditing(transaction); setForm(next); setInitialForm(next); setDrawerOpen(true)
  }

  function requestClose() {
    if (formIsDirty) setConfirmExit(true)
    else { setDrawerOpen(false); setInitialForm(null); setEditing(null) }
  }

  function changeType(nextType: TransactionType) {
    setForm({ ...form, type: nextType, category_id: categories.find((category) => category.type === nextType)?.id ?? '', installments: nextType === 'Receita' ? 1 : form.installments })
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null)
    try {
      if (editing) { const { installments: _installments, ...update } = form; await api.transactions.update(editing.id, update) }
      else await api.transactions.create(form)
      setDrawerOpen(false); setInitialForm(null); setEditing(null); await load()
    }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setSaving(true); setError(null)
    try { await api.transactions.delete(pendingDelete.id); setPendingDelete(null); await load() }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  async function confirmDeleteSeries() {
    if (!pendingDelete?.installment_group_id) return
    setSaving(true); setError(null)
    try { await api.transactions.deleteSeries(pendingDelete.installment_group_id); setPendingDelete(null); await load() }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  const accountName = (id: string) => accounts.find((account) => account.id === id)?.name ?? 'Conta removida'
  const categoryName = (id: string) => categories.find((category) => category.id === id)?.name ?? 'Sem categoria'

  return <>
    <header className="topbar transactions-header"><div><p className="eyebrow">FLUXO FINANCEIRO</p><h1>Transações</h1><p className="subtitle">Visualize receitas e despesas em um só lugar.</p></div><button className="primary-button" type="button" onClick={openCreate} disabled={!accounts.length}><span>＋</span> Nova transação</button></header>
    {error && <section className="error-state" role="alert"><div><strong>Não foi possível concluir a operação</strong><p>{error}</p></div><button type="button" onClick={() => setError(null)}>Fechar</button></section>}
    {!accounts.length && !loading && <section className="notice-state">Crie uma conta antes de registrar sua primeira transação.</section>}

    <section className="transaction-summary">
      <div className="summary-income"><span>Receitas filtradas</span><strong>{currency.format(income)}</strong></div>
      <div className="summary-expense"><span>Despesas filtradas</span><strong>{currency.format(expense)}</strong></div>
      <div><span>Resultado</span><strong>{currency.format(income - expense)}</strong></div>
    </section>

    <section className="transaction-filters" aria-label="Filtros de transações">
      <label>Mês<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label>
      <label>Tipo<select value={type} onChange={(event) => setType(event.target.value as 'Todos' | TransactionType)}><option>Todos</option><option>Receita</option><option>Despesa</option></select></label>
      <label>Conta<select value={accountFilter} onChange={(event) => setAccountFilter(event.target.value)}><option>Todos</option>{accounts.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}</select></label>
      <button type="button" onClick={() => { setMonth(''); setType('Todos'); setAccountFilter('Todos') }}>Limpar filtros</button>
    </section>

    <section className="transactions-panel">
      {loading ? <div className="transactions-loading"><i /><i /><i /></div> : filtered.length ? <div className="transaction-table">
        <div className="transaction-table-head"><span>Descrição</span><span>Conta</span><span>Data</span><span>Valor</span><span /></div>
        {filtered.map((transaction) => <div className="transaction-table-row" key={transaction.id}>
          <div className="transaction-main"><span className={transaction.type === 'Receita' ? 'income-icon' : 'expense-icon'}>{transaction.type === 'Receita' ? '↗' : '↘'}</span><div><strong>{transaction.description}</strong><small>{categoryName(transaction.category_id)}{transaction.description.match(/\(\d+\/\d+\)$/) && <b>Parcelada</b>}</small></div></div>
          <span data-label="Conta">{accountName(transaction.account_id)}</span><span data-label="Data">{formatDate(transaction.date)}</span>
          <strong className={transaction.type === 'Receita' ? 'positive' : 'negative'} data-label="Valor">{transaction.type === 'Receita' ? '+' : '−'} {currency.format(transaction.amount)}</strong>
          <div className="row-actions"><button type="button" onClick={() => openEdit(transaction)} aria-label={`Editar ${transaction.description}`}>✎</button><button className="row-delete" type="button" onClick={() => setPendingDelete(transaction)} aria-label={`Excluir ${transaction.description}`}>×</button></div>
        </div>)}
      </div> : <div className="transactions-empty"><span>↔</span><h2>Nenhuma transação encontrada</h2><p>Ajuste os filtros ou registre um novo lançamento.</p></div>}
    </section>

    <section className="forecast-panel">
      <div className="forecast-heading"><div><p className="eyebrow">PRÓXIMOS 6 MESES</p><h2>Previsão de despesas por conta</h2></div><p>Inclui parcelas futuras já programadas.</p></div>
      <div className="forecast-grid">{forecast.map((item) => <article className="forecast-month" key={item.month}>
        <div className="forecast-month-total"><span>{item.label}</span><strong>{currency.format(item.total)}</strong></div>
        {item.accounts.length ? <div className="forecast-accounts">{item.accounts.map((account) => <div key={account.accountId}>
          <div><span>{account.accountName}</span><b>{currency.format(account.amount)}</b></div>
          <i><span style={{ width: `${account.percentage}%` }} /></i>
        </div>)}</div> : <p className="forecast-empty">Sem despesas previstas</p>}
      </article>)}</div>
    </section>

    {drawerOpen && <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}><aside className="account-drawer transaction-drawer" aria-label={editing ? 'Editar transação' : 'Nova transação'}><div className="drawer-heading"><div><p className="eyebrow">{editing ? 'ATUALIZAÇÃO' : 'NOVO LANÇAMENTO'}</p><h2>{editing ? 'Editar transação' : 'Nova transação'}</h2></div><button className="close-button" type="button" onClick={requestClose}>×</button></div><form onSubmit={(event) => void submit(event)}>
      <div className="type-switch"><button className={form.type === 'Despesa' ? 'active expense' : ''} type="button" onClick={() => changeType('Despesa')}>Despesa</button><button className={form.type === 'Receita' ? 'active income' : ''} type="button" onClick={() => changeType('Receita')}>Receita</button></div>
      <label>Descrição<input required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Ex.: Compras do mês" /></label>
      <label>Valor<div className="money-input"><span>R$</span><input required min="0.01" type="number" step="0.01" placeholder="0.00" value={form.amount === 0 ? '' : form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value === '' ? 0 : Number(event.target.value) })} /></div></label>
      <div className="form-columns"><label>Data<input required type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></label>{form.type === 'Despesa' && !editing && <label>Parcelas<input required min="1" max="120" type="number" placeholder="1" value={form.installments <= 0 ? '' : form.installments} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setForm({ ...form, installments: event.target.value === '' ? 0 : Number(event.target.value) })} /></label>}</div>
      {editing?.installment_group_id && <p className="form-note">Você está editando somente a parcela {editing.installment_number} de {editing.installment_total}. As demais permanecem inalteradas.</p>}
      <label>Conta<select required value={form.account_id} onChange={(event) => setForm({ ...form, account_id: event.target.value })}><option value="" disabled>Selecione</option>{accounts.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}</select></label>
      <label>Categoria<select required value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })}><option value="" disabled>Selecione</option>{availableCategories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label>
      <label className="check-field"><input type="checkbox" checked={form.is_fixed} onChange={(event) => setForm({ ...form, is_fixed: event.target.checked })} /><span>Marcar como transação fixa</span></label>
      <div className="drawer-actions"><button className="secondary-button" type="button" onClick={requestClose}>Cancelar</button><button className="primary-button" disabled={saving} type="submit">{saving ? 'Salvando…' : editing ? 'Salvar alteração' : 'Criar transação'}</button></div>
    </form></aside></div>}

    {pendingDelete && <ConfirmDialog title={pendingDelete.installment_group_id ? 'Excluir compra parcelada?' : 'Excluir transação?'} message={pendingDelete.installment_group_id ? <>Esta é a parcela <strong>{pendingDelete.installment_number} de {pendingDelete.installment_total}</strong>. Você pode excluir somente ela ou todas as parcelas da série.</> : <>O valor de <strong>{currency.format(pendingDelete.amount)}</strong> será estornado na conta vinculada.</>} confirmLabel={pendingDelete.installment_group_id ? 'Toda a série' : 'Excluir'} alternateLabel={pendingDelete.installment_group_id ? 'Só esta parcela' : undefined} tone="danger" busy={saving} onCancel={() => setPendingDelete(null)} onAlternate={() => void confirmDelete()} onConfirm={() => pendingDelete.installment_group_id ? void confirmDeleteSeries() : void confirmDelete()} />}
    {confirmExit && <ConfirmDialog title="Descartar alterações?" message="As informações preenchidas nesta transação serão perdidas." confirmLabel="Descartar" onCancel={() => setConfirmExit(false)} onConfirm={() => { setConfirmExit(false); setDrawerOpen(false); setInitialForm(null); setEditing(null) }} />}
  </>
}

function formatDate(value: string) { return new Intl.DateTimeFormat('pt-BR').format(new Date(`${value}T12:00:00`)) }
function messageFrom(error: unknown) { return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.' }
