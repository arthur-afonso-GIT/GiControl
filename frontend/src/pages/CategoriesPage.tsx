import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Category, CategoryWrite, TransactionType } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import './CategoriesPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const emptyCategory: CategoryWrite = { name: '', type: 'Despesa', monthly_limit: 0 }

export function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<Category | null>(null)
  const [form, setForm] = useState<CategoryWrite>(emptyCategory)
  const [initialForm, setInitialForm] = useState<CategoryWrite | null>(null)
  const [confirmExit, setConfirmExit] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<Category | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setCategories(await api.categories.list()) }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setLoading(false) }
  }, [])

  // oxlint-disable-next-line react/set-state-in-effect -- sincroniza a página com a API ao montar.
  useEffect(() => { void load() }, [load])

  function openCreate() {
    setEditing(null); setForm(emptyCategory); setInitialForm(emptyCategory); setDrawerOpen(true)
  }

  function openEdit(category: Category) {
    const next = { name: category.name, type: category.type, monthly_limit: category.monthly_limit }
    setEditing(category); setForm(next); setInitialForm(next); setDrawerOpen(true)
  }

  function requestClose() {
    if (initialForm !== null && JSON.stringify(form) !== JSON.stringify(initialForm)) setConfirmExit(true)
    else closeDrawer()
  }

  function closeDrawer() { setDrawerOpen(false); setInitialForm(null); setEditing(null) }

  function changeType(type: TransactionType) {
    setForm({ ...form, type, monthly_limit: type === 'Receita' ? 0 : form.monthly_limit })
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null)
    try {
      if (editing) await api.categories.update(editing.id, form)
      else await api.categories.create(form)
      closeDrawer(); await load()
    } catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setSaving(true); setError(null)
    try { await api.categories.delete(pendingDelete.id); setPendingDelete(null); await load() }
    catch (requestError) { setError(messageFrom(requestError)) }
    finally { setSaving(false) }
  }

  const expenses = categories.filter((category) => category.type === 'Despesa')
  const incomes = categories.filter((category) => category.type === 'Receita')
  const totalLimits = expenses.reduce((sum, category) => sum + category.monthly_limit, 0)

  return <>
    <header className="topbar categories-header"><div><p className="eyebrow">ORGANIZAÇÃO</p><h1>Categorias</h1><p className="subtitle">Classifique seus lançamentos e defina limites mensais.</p></div><button className="primary-button" type="button" onClick={openCreate}><span>＋</span> Nova categoria</button></header>
    {error && <section className="error-state" role="alert"><div><strong>Não foi possível concluir a operação</strong><p>{error}</p></div><button type="button" onClick={() => setError(null)}>Fechar</button></section>}

    <section className="category-summary">
      <div><span>Categorias de despesa</span><strong>{expenses.length}</strong></div>
      <div><span>Categorias de receita</span><strong>{incomes.length}</strong></div>
      <div><span>Limites mensais</span><strong>{currency.format(totalLimits)}</strong></div>
    </section>

    {loading ? <section className="category-columns category-loading"><i /><i /></section> : <section className="category-columns">
      <CategoryGroup title="Despesas" subtitle="Limites ajudam a controlar o orçamento" categories={expenses} onEdit={openEdit} onDelete={setPendingDelete} />
      <CategoryGroup title="Receitas" subtitle="Fontes que compõem sua renda" categories={incomes} onEdit={openEdit} onDelete={setPendingDelete} />
    </section>}

    {drawerOpen && <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && requestClose()}><aside className="account-drawer category-drawer" aria-label={editing ? 'Editar categoria' : 'Nova categoria'}>
      <div className="drawer-heading"><div><p className="eyebrow">{editing ? 'ATUALIZAÇÃO' : 'CADASTRO'}</p><h2>{editing ? editing.name : 'Nova categoria'}</h2></div><button className="close-button" type="button" onClick={requestClose} aria-label="Fechar">×</button></div>
      <form onSubmit={(event) => void submit(event)}>
        <div className="type-switch"><button className={form.type === 'Despesa' ? 'active expense' : ''} type="button" onClick={() => changeType('Despesa')}>Despesa</button><button className={form.type === 'Receita' ? 'active income' : ''} type="button" onClick={() => changeType('Receita')}>Receita</button></div>
        <label>Nome<input required maxLength={80} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Ex.: Alimentação" /></label>
        {form.type === 'Despesa' && <label>Limite mensal<div className="money-input"><span>R$</span><input min="0" type="number" step="0.01" placeholder="Sem limite" value={form.monthly_limit === 0 ? '' : form.monthly_limit} onFocus={(event) => event.currentTarget.select()} onChange={(event) => setForm({ ...form, monthly_limit: event.target.value === '' ? 0 : Number(event.target.value) })} /></div><small className="field-help">Deixe vazio se não quiser definir um teto.</small></label>}
        <div className="drawer-actions"><button className="secondary-button" type="button" onClick={requestClose}>Cancelar</button><button className="primary-button" disabled={saving} type="submit">{saving ? 'Salvando…' : editing ? 'Salvar alterações' : 'Criar categoria'}</button></div>
      </form>
    </aside></div>}

    {pendingDelete && <ConfirmDialog title="Excluir categoria?" message={<>A categoria <strong>{pendingDelete.name}</strong> será removida. As transações existentes serão preservadas.</>} confirmLabel="Excluir" tone="danger" busy={saving} onCancel={() => setPendingDelete(null)} onConfirm={() => void confirmDelete()} />}
    {confirmExit && <ConfirmDialog title="Descartar alterações?" message="As informações preenchidas nesta categoria serão perdidas." confirmLabel="Descartar" onCancel={() => setConfirmExit(false)} onConfirm={() => { setConfirmExit(false); closeDrawer() }} />}
  </>
}

type CategoryGroupProps = { title: string; subtitle: string; categories: Category[]; onEdit: (category: Category) => void; onDelete: (category: Category) => void }
function CategoryGroup({ title, subtitle, categories, onEdit, onDelete }: CategoryGroupProps) {
  return <article className="category-group"><div className="category-group-heading"><div><h2>{title}</h2><p>{subtitle}</p></div><span>{categories.length}</span></div>
    {categories.length ? <div className="category-list">{categories.map((category) => <div className="category-row" key={category.id}>
      <span className={`category-symbol ${category.type === 'Despesa' ? 'expense' : 'income'}`}>{category.name.slice(0, 1).toUpperCase()}</span>
      <div><strong>{category.name}</strong><small>{category.type === 'Despesa' && category.monthly_limit > 0 ? `Limite de ${currency.format(category.monthly_limit)}` : category.type === 'Despesa' ? 'Sem limite mensal' : 'Fonte de receita'}</small></div>
      <div className="category-actions"><button type="button" onClick={() => onEdit(category)}>Editar</button><button type="button" onClick={() => onDelete(category)} aria-label={`Excluir ${category.name}`}>×</button></div>
    </div>)}</div> : <div className="category-empty">Nenhuma categoria neste grupo.</div>}
  </article>
}

function messageFrom(error: unknown) { return error instanceof Error ? error.message : 'Ocorreu um erro inesperado.' }
