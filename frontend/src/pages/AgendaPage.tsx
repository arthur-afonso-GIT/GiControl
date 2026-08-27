import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Account, Category, ExpenseOccurrence, RecurringExpense, RecurringExpenseWrite } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import './AgendaPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const today = () => new Date().toISOString().slice(0, 10)
const currentMonth = () => today().slice(0, 7)
const empty = (): RecurringExpenseWrite => ({ name: '', amount: 0, account_id: '', category_id: '', due_day: 1, start_date: today(), end_date: null, active: true })
type AgendaFilter = 'Todos' | 'Pendentes' | 'Pagos' | 'Vencidos'

export function AgendaPage() {
  const [items, setItems] = useState<ExpenseOccurrence[]>([])
  const [schedules, setSchedules] = useState<RecurringExpense[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [month, setMonth] = useState(currentMonth)
  const [form, setForm] = useState<RecurringExpenseWrite>(empty)
  const [initialForm, setInitialForm] = useState<RecurringExpenseWrite | null>(null)
  const [editing, setEditing] = useState<RecurringExpense | null>(null)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<RecurringExpense | null>(null)
  const [confirmExit, setConfirmExit] = useState(false)
  const [oneOff, setOneOff] = useState(false)
  const [postponing, setPostponing] = useState<ExpenseOccurrence | null>(null)
  const [postponedDate, setPostponedDate] = useState('')
  const [pendingSkip, setPendingSkip] = useState<ExpenseOccurrence | null>(null)
  const [filter, setFilter] = useState<AgendaFilter>('Todos')

  const load = useCallback(async () => {
    try {
      const [occurrences, scheduleData, accountData, categoryData] = await Promise.all([api.recurringExpenses.occurrences(month), api.recurringExpenses.list(), api.accounts.list(), api.categories.list()])
      setItems(occurrences); setSchedules(scheduleData); setAccounts(accountData); setCategories(categoryData.filter((item) => item.type === 'Despesa'))
    } catch (requestError) { setError(messageFrom(requestError)) }
  }, [month])
  // oxlint-disable-next-line react/set-state-in-effect -- sincroniza agenda com o mês selecionado.
  useEffect(() => { void load() }, [load])

  function openCreate(isOneOff = false) { const next = empty(); next.account_id = accounts[0]?.id ?? ''; next.category_id = categories[0]?.id ?? ''; setOneOff(isOneOff); setEditing(null); setForm(next); setInitialForm(next); setOpen(true) }
  function openEdit(item: RecurringExpense) { const next = toWrite(item); setEditing(item); setForm(next); setInitialForm(next); setOpen(true) }
  function closeDrawer() { setOpen(false); setEditing(null); setInitialForm(null) }
  function requestClose() { if (initialForm && JSON.stringify(form) !== JSON.stringify(initialForm)) setConfirmExit(true); else closeDrawer() }
  async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { const payload = oneOff ? { ...form, due_day: Number(form.start_date.slice(8, 10)), end_date: form.start_date } : form; if (editing) await api.recurringExpenses.update(editing.id, payload); else await api.recurringExpenses.create(payload); closeDrawer(); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  async function toggle(item: RecurringExpense) { setSaving(true); try { await api.recurringExpenses.update(item.id, { ...toWrite(item), active: !item.active }); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  async function confirm(item: ExpenseOccurrence) { setSaving(true); try { await api.recurringExpenses.confirm(item.id, month); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  async function remove() { if (!pendingDelete) return; setSaving(true); try { await api.recurringExpenses.delete(pendingDelete.id); setPendingDelete(null); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  async function postpone() { if (!postponing || !postponedDate) return; setSaving(true); try { await api.recurringExpenses.changeOccurrence(postponing.id, month, { due_date: postponedDate }); setPostponing(null); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  async function skip() { if (!pendingSkip) return; setSaving(true); try { await api.recurringExpenses.changeOccurrence(pendingSkip.id, month, { skipped: true }); setPendingSkip(null); await load() } catch (requestError) { setError(messageFrom(requestError)) } finally { setSaving(false) } }
  const total = items.filter((item) => !item.confirmed).reduce((sum, item) => sum + item.amount, 0)
  const visibleItems = items.filter((item) => filter === 'Todos' || (filter === 'Pagos' && item.confirmed) || (filter === 'Pendentes' && !item.confirmed) || (filter === 'Vencidos' && !item.confirmed && item.due_date < today()))

  return <><header className="topbar"><div><p className="eyebrow">PLANEJAMENTO</p><h1>Agenda financeira</h1><p className="subtitle">Acompanhe vencimentos e confirme somente o que foi pago.</p></div><div className="agenda-create-actions"><button className="secondary-button" type="button" onClick={() => openCreate(true)}>＋ Despesa avulsa</button><button className="primary-button" type="button" onClick={() => openCreate(false)}>＋ Despesa fixa</button></div></header>
    {error && <section className="error-state" role="alert"><div><strong>Não foi possível concluir</strong><p>{error}</p></div><button onClick={() => setError(null)}>Fechar</button></section>}
    <section className="agenda-toolbar"><label>Mês<input type="month" value={month} onChange={(event) => setMonth(event.target.value || currentMonth())} /></label><div className="agenda-filters" aria-label="Filtrar compromissos">{(['Todos', 'Pendentes', 'Pagos', 'Vencidos'] as AgendaFilter[]).map((value) => <button className={filter === value ? 'active' : ''} type="button" key={value} onClick={() => setFilter(value)}>{value}</button>)}</div><div><span>Pendente no mês</span><strong>{currency.format(total)}</strong></div></section>
    <section className="agenda-list">{visibleItems.length ? visibleItems.map((item) => <OccurrenceRow key={item.id} item={item} accounts={accounts} categories={categories} saving={saving} onConfirm={confirm} onPostpone={(value) => { setPostponing(value); setPostponedDate(value.due_date) }} onSkip={setPendingSkip} />) : <div className="agenda-empty"><strong>Nenhum compromisso encontrado</strong><p>{items.length ? 'Tente outro filtro para ver os compromissos do mês.' : 'Cadastre despesas fixas para planejar seus próximos vencimentos.'}</p></div>}</section>
    <section className="schedule-panel"><div className="schedule-heading"><div><p className="eyebrow">CONFIGURAÇÃO</p><h2>Compromissos cadastrados</h2></div><span>{schedules.length}</span></div>{schedules.map((item) => <div className={`schedule-row ${item.active ? '' : 'paused'}`} key={item.id}><div><strong>{item.name}</strong><small>Todo dia {item.due_day}{item.end_date ? ` · até ${formatDate(item.end_date)}` : ' · sem término'}</small></div><b>{currency.format(item.amount)}</b><button onClick={() => openEdit(item)}>Editar</button><button onClick={() => void toggle(item)}>{item.active ? 'Pausar' : 'Ativar'}</button><button className="danger-action" onClick={() => setPendingDelete(item)}>Excluir</button></div>)}</section>
    {open && <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}><aside className="account-drawer"><div className="drawer-heading"><div><p className="eyebrow">{editing ? 'ATUALIZAÇÃO' : 'NOVO COMPROMISSO'}</p><h2>{editing ? 'Editar despesa fixa' : oneOff ? 'Despesa avulsa' : 'Despesa fixa'}</h2></div><button className="close-button" onClick={requestClose}>×</button></div><form onSubmit={(event) => void submit(event)}><label>Descrição<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Valor<div className="money-input"><span>R$</span><input required min="0.01" step="0.01" type="number" value={form.amount || ''} onChange={(event) => setForm({ ...form, amount: Number(event.target.value) })} /></div></label>{!oneOff && <label>Dia do vencimento<input required min="1" max="31" type="number" value={form.due_day} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setForm({ ...form, due_day: Number(event.target.value) })} /></label>}<div className="form-columns"><label>{oneOff ? 'Data do vencimento' : 'Início'}<input required type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} /></label>{!oneOff && <label>Término opcional<input type="date" min={form.start_date} value={form.end_date ?? ''} onChange={(event) => setForm({ ...form, end_date: event.target.value || null })} /></label>}</div><label>Conta<select required value={form.account_id} onChange={(event) => setForm({ ...form, account_id: event.target.value })}>{accounts.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}</select></label><label>Categoria<select required value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })}>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label>{!oneOff && <label className="check-field"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /><span>Compromisso ativo</span></label>}<div className="drawer-actions"><button className="secondary-button" type="button" onClick={requestClose}>Cancelar</button><button className="primary-button" disabled={saving}>{editing ? 'Salvar alterações' : 'Salvar despesa'}</button></div></form></aside></div>}
    {pendingDelete && <ConfirmDialog title="Excluir despesa fixa?" message="Pagamentos confirmados serão preservados; apenas os próximos vencimentos deixarão de aparecer." confirmLabel="Excluir" tone="danger" busy={saving} onCancel={() => setPendingDelete(null)} onConfirm={() => void remove()} />}
    {confirmExit && <ConfirmDialog title="Descartar alterações?" message="As mudanças feitas neste compromisso serão perdidas." confirmLabel="Descartar" onCancel={() => setConfirmExit(false)} onConfirm={() => { setConfirmExit(false); closeDrawer() }} />}
    {pendingSkip && <ConfirmDialog title="Cancelar somente este mês?" message="A regra continuará ativa nos próximos meses e nenhum valor será retirado do saldo agora." confirmLabel="Cancelar ocorrência" tone="danger" busy={saving} onCancel={() => setPendingSkip(null)} onConfirm={() => void skip()} />}
    {postponing && <div className="dialog-backdrop"><div className="confirm-dialog" role="dialog" aria-modal="true"><span className="dialog-icon primary">↗</span><h2>Adiar vencimento</h2><div className="dialog-message"><label className="postpone-field">Nova data<input type="date" min={`${month}-01`} max={`${month}-31`} value={postponedDate} onChange={(event) => setPostponedDate(event.target.value)} /></label></div><div className="dialog-actions"><button className="secondary-button" onClick={() => setPostponing(null)}>Cancelar</button><button className="primary-button" disabled={saving || !postponedDate} onClick={() => void postpone()}>Adiar</button></div></div></div>}
  </>
}

function OccurrenceRow({ item, accounts, categories, saving, onConfirm, onPostpone, onSkip }: { item: ExpenseOccurrence; accounts: Account[]; categories: Category[]; saving: boolean; onConfirm: (item: ExpenseOccurrence) => Promise<void>; onPostpone: (item: ExpenseOccurrence) => void; onSkip: (item: ExpenseOccurrence) => void }) { const canConfirm = item.due_date <= today(); const overdue = canConfirm && !item.confirmed; return <article className={`agenda-item ${item.confirmed ? 'paid' : overdue ? 'overdue' : ''}`}><span className="agenda-date"><b>{new Date(`${item.due_date}T12:00:00`).getDate()}</b><small>{new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(new Date(`${item.due_date}T12:00:00`))}</small></span><div><strong>{item.name}</strong><small>{accounts.find((account) => account.id === item.account_id)?.name ?? 'Conta removida'} · {categories.find((category) => category.id === item.category_id)?.name ?? 'Categoria removida'}{overdue ? ' · Vencida' : ''}</small></div><b>{currency.format(item.amount)}</b>{item.confirmed ? <span className="agenda-status">Pago</span> : <div className="occurrence-actions">{canConfirm && <button className="primary-button" disabled={saving} onClick={() => void onConfirm(item)}>Confirmar</button>}<button onClick={() => onPostpone(item)}>Adiar</button><button onClick={() => onSkip(item)}>Cancelar mês</button></div>}</article> }
function toWrite(item: RecurringExpense): RecurringExpenseWrite { const { id: _id, ...write } = item; return write }
function formatDate(value: string) { return new Intl.DateTimeFormat('pt-BR').format(new Date(`${value}T12:00:00`)) }
function messageFrom(error: unknown) { return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.' }
