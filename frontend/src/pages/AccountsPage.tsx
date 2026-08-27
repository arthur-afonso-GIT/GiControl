import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Account, AccountCreate, AccountType, Category } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import './AccountsPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const accountTypes: AccountType[] = ['Conta Corrente', 'Carteira', 'Poupança', 'Cartão']
const today = () => new Date().toISOString().slice(0, 10)
const emptyAccount: AccountCreate = { name: '', type: 'Conta Corrente', initial_balance: 0, monthly_income: 0, income_day: null, income_category_id: null, income_start_date: today() }

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [incomeCategories, setIncomeCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)
  const [form, setForm] = useState<AccountCreate>(emptyAccount)
  const [initialForm, setInitialForm] = useState<AccountCreate | null>(null)
  const [confirmExit, setConfirmExit] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<Account | null>(null)

  const loadAccounts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { const [accountData, categoryData] = await Promise.all([api.accounts.list(), api.categories.list()]); setAccounts(accountData); setIncomeCategories(categoryData.filter((item) => item.type === 'Receita')) }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setLoading(false) }
  }, [])

  // oxlint-disable-next-line react/set-state-in-effect -- sincroniza a página com a API ao montar.
  useEffect(() => { void loadAccounts() }, [loadAccounts])

  function openCreate() {
    setEditing(null)
    setForm(emptyAccount)
    setInitialForm(emptyAccount)
    setFormOpen(true)
  }

  function openEdit(account: Account) {
    setEditing(account)
    const next = { name: account.name, type: account.type, initial_balance: account.balance, monthly_income: account.monthly_income, income_day: account.income_day, income_category_id: account.income_category_id, income_start_date: account.income_start_date ?? today() }
    setForm(next)
    setInitialForm(next)
    setFormOpen(true)
  }

  function requestClose() {
    if (initialForm !== null && JSON.stringify(form) !== JSON.stringify(initialForm)) setConfirmExit(true)
    else { setFormOpen(false); setInitialForm(null) }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      if (editing) {
        await api.accounts.updateBalance(editing.id, form.initial_balance)
        await api.accounts.updateIncomeSchedule(editing.id, { monthly_income: form.monthly_income, income_day: form.income_day, income_category_id: form.income_category_id, income_start_date: form.income_start_date })
      } else {
        await api.accounts.create(form)
      }
      setFormOpen(false)
      setInitialForm(null)
      await loadAccounts()
    } catch (requestError) {
      setError(messageFrom(requestError))
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!pendingDelete) return
    setError(null)
    setSaving(true)
    try {
      await api.accounts.delete(pendingDelete.id)
      setPendingDelete(null)
      await loadAccounts()
    } catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  const totalBalance = accounts.reduce((total, account) => total + account.balance, 0)

  return <>
    <header className="topbar accounts-header">
      <div><p className="eyebrow">PATRIMÔNIO</p><h1>Suas contas</h1><p className="subtitle">Organize saldos, carteiras e rendas recorrentes.</p></div>
      <button className="primary-button" type="button" onClick={openCreate}><span aria-hidden="true">＋</span> Nova conta</button>
    </header>

    {error && <section className="error-state" role="alert"><div><strong>Não foi possível concluir a operação</strong><p>{error}</p></div><button type="button" onClick={() => setError(null)}>Fechar</button></section>}

    <section className="accounts-summary">
      <div><span>Saldo consolidado</span><strong>{currency.format(totalBalance)}</strong></div>
      <div><span>Contas ativas</span><strong>{accounts.length}</strong></div>
      <div><span>Renda mensal prevista</span><strong>{currency.format(accounts.reduce((total, account) => total + account.monthly_income, 0))}</strong></div>
    </section>

    {loading ? <section className="account-grid account-loading"><i /><i /><i /></section>
      : accounts.length ? <section className="account-grid">{accounts.map((account, index) => (
        <article className="account-card" key={account.id}>
          <div className="account-card-top"><span className={`account-orb orb-${index % 3}`}>{account.name.slice(0, 1).toUpperCase()}</span><span className="account-type">{account.type}</span></div>
          <p>{account.name}</p><strong>{currency.format(account.balance)}</strong>
          <div className="account-income"><span>Renda mensal</span><b>{currency.format(account.monthly_income)}</b></div>
          <div className="account-actions"><button type="button" onClick={() => openEdit(account)}>Editar valores</button><button className="danger-action" type="button" onClick={() => setPendingDelete(account)}>Excluir</button></div>
        </article>
      ))}</section>
      : <section className="accounts-empty"><span>◫</span><h2>Crie sua primeira conta</h2><p>Adicione uma conta bancária, carteira ou cartão para começar.</p><button className="primary-button" type="button" onClick={openCreate}>Nova conta</button></section>}

    {formOpen && <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}>
      <aside className="account-drawer" aria-label={editing ? 'Editar conta' : 'Nova conta'}>
        <div className="drawer-heading"><div><p className="eyebrow">{editing ? 'ATUALIZAÇÃO' : 'CADASTRO'}</p><h2>{editing ? editing.name : 'Nova conta'}</h2></div><button className="close-button" type="button" onClick={requestClose} aria-label="Fechar">×</button></div>
        <form onSubmit={(event) => void submit(event)}>
          {!editing && <><label>Nome da conta<input required maxLength={80} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Ex.: Conta principal" /></label><label>Tipo<select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as AccountType })}>{accountTypes.map((type) => <option key={type}>{type}</option>)}</select></label></>}
          <label>{editing ? 'Saldo atual' : 'Saldo inicial'}<div className="money-input"><span>R$</span><input type="number" step="0.01" placeholder="0.00" value={form.initial_balance === 0 ? '' : form.initial_balance} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setForm({ ...form, initial_balance: event.target.value === '' ? 0 : Number(event.target.value) })} /></div></label>
          <label>Renda mensal prevista<div className="money-input"><span>R$</span><input min="0" type="number" step="0.01" placeholder="0.00" value={form.monthly_income === 0 ? '' : form.monthly_income} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setForm({ ...form, monthly_income: event.target.value === '' ? 0 : Number(event.target.value) })} /></div></label>
          {form.monthly_income > 0 && <><div className="form-columns"><label>Dia do recebimento<input required min="1" max="31" type="number" value={form.income_day ?? ''} onChange={(event) => setForm({ ...form, income_day: event.target.value === '' ? null : Number(event.target.value) })} /></label><label>Início<input required type="date" value={form.income_start_date ?? ''} onChange={(event) => setForm({ ...form, income_start_date: event.target.value })} /></label></div><label>Categoria da receita<select required value={form.income_category_id ?? ''} onChange={(event) => setForm({ ...form, income_category_id: event.target.value })}><option value="" disabled>Selecione</option>{incomeCategories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label><p className="form-note">A renda aparecerá como prevista e só entrará no saldo após sua confirmação.</p></>}
          {editing && <p className="form-note">Nome e tipo permanecem preservados nesta primeira versão.</p>}
          <div className="drawer-actions"><button className="secondary-button" type="button" onClick={requestClose}>Cancelar</button><button className="primary-button" disabled={saving} type="submit">{saving ? 'Salvando…' : editing ? 'Salvar alterações' : 'Criar conta'}</button></div>
        </form>
      </aside>
    </div>}
    {pendingDelete && <ConfirmDialog title="Excluir conta?" message={<>A conta <strong>{pendingDelete.name}</strong> e todas as transações vinculadas serão excluídas.</>} confirmLabel="Excluir" tone="danger" busy={saving} onCancel={() => setPendingDelete(null)} onConfirm={() => void remove()} />}
    {confirmExit && <ConfirmDialog title="Descartar alterações?" message="As informações preenchidas nesta conta serão perdidas." confirmLabel="Descartar" onCancel={() => setConfirmExit(false)} onConfirm={() => { setConfirmExit(false); setFormOpen(false); setInitialForm(null) }} />}
  </>
}

function messageFrom(error: unknown) { return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.' }
