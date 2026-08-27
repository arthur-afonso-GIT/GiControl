import type { Account, AccountCreate, AgendaSummary, CardInstallment, CardInvoice, CardInvoiceDetail, CardPurchase, CardPurchaseWrite, Category, CategoryBudget, CategoryWrite, CreditCard, CreditCardWrite, DashboardMetrics, ExpenseOccurrence, Health, MonthlyReport, RecurringExpense, RecurringExpenseWrite, ScheduledIncome, Transaction, TransactionCreate, TransactionUpdate } from './types'
import { accessToken } from '../auth/supabase'

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = await accessToken()
  const response = await fetch(`/api${path}`, {
    method: options.method ?? 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `A API respondeu com o status ${response.status}.`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/health'),
  dashboard: (month?: string) => request<DashboardMetrics>(`/dashboard${month ? `?month=${encodeURIComponent(month)}` : ''}`),
  budgets: (month?: string) => request<CategoryBudget[]>(`/budgets${month ? `?month=${encodeURIComponent(month)}` : ''}`),
  monthlyReport: (month: string) => request<MonthlyReport>(`/reports/monthly?month=${encodeURIComponent(month)}`),
  agendaSummary: (month: string) => request<AgendaSummary>(`/agenda-summary?month=${encodeURIComponent(month)}`),
  scheduledIncomes: {
    list: (month: string) => request<ScheduledIncome[]>(`/scheduled-incomes?month=${encodeURIComponent(month)}`),
    confirm: (accountId: string, month: string) => request<Transaction>(`/scheduled-incomes/${accountId}/${month}/confirm`, { method: 'POST' }),
  },
  recurringExpenses: {
    list: () => request<RecurringExpense[]>('/recurring-expenses'),
    occurrences: (month: string) => request<ExpenseOccurrence[]>(`/expense-occurrences?month=${encodeURIComponent(month)}`),
    create: (item: RecurringExpenseWrite) => request<RecurringExpense>('/recurring-expenses', { method: 'POST', body: item }),
    update: (id: string, item: RecurringExpenseWrite) => request<RecurringExpense>(`/recurring-expenses/${id}`, { method: 'PUT', body: item }),
    delete: (id: string) => request<void>(`/recurring-expenses/${id}`, { method: 'DELETE' }),
    confirm: (id: string, month: string) => request<Transaction>(`/expense-occurrences/${id}/${month}/confirm`, { method: 'POST' }),
    changeOccurrence: (id: string, month: string, change: { due_date?: string | null; skipped?: boolean }) => request<RecurringExpense>(`/expense-occurrences/${id}/${month}`, { method: 'PUT', body: change }),
  },
  accounts: {
    list: () => request<Account[]>('/accounts'),
    create: (account: AccountCreate) => request<Account>('/accounts', { method: 'POST', body: account }),
    updateBalance: (accountId: string, value: number) => request<Account>(`/accounts/${accountId}/balance`, { method: 'PATCH', body: { value } }),
    updateMonthlyIncome: (accountId: string, value: number) => request<Account>(`/accounts/${accountId}/monthly-income`, { method: 'PATCH', body: { value } }),
    updateIncomeSchedule: (accountId: string, schedule: Omit<AccountCreate, 'name' | 'type' | 'initial_balance'>) => request<Account>(`/accounts/${accountId}/income-schedule`, { method: 'PUT', body: schedule }),
    delete: (accountId: string) => request<void>(`/accounts/${accountId}`, { method: 'DELETE' }),
  },
  categories: {
    list: () => request<Category[]>('/categories'),
    create: (category: CategoryWrite) => request<Category>('/categories', { method: 'POST', body: category }),
    update: (categoryId: string, category: CategoryWrite) => request<Category>(`/categories/${categoryId}`, { method: 'PUT', body: category }),
    delete: (categoryId: string) => request<void>(`/categories/${categoryId}`, { method: 'DELETE' }),
  },
  transactions: {
    list: () => request<Transaction[]>('/transactions'),
    create: (transaction: TransactionCreate) => request<Transaction[]>('/transactions', { method: 'POST', body: transaction }),
    update: (transactionId: string, transaction: TransactionUpdate) => request<Transaction>(`/transactions/${transactionId}`, { method: 'PUT', body: transaction }),
    delete: (transactionId: string) => request<void>(`/transactions/${transactionId}`, { method: 'DELETE' }),
    deleteSeries: (groupId: string) => request<void>(`/transaction-series/${groupId}`, { method: 'DELETE' }),
  },
  creditCards: {
    list: () => request<CreditCard[]>('/credit-cards'),
    create: (card: CreditCardWrite) => request<CreditCard>('/credit-cards', { method: 'POST', body: card }),
    update: (cardId: string, card: CreditCardWrite) => request<CreditCard>(`/credit-cards/${cardId}`, { method: 'PUT', body: card }),
    purchase: (cardId: string, purchase: CardPurchaseWrite) => request<{ purchase: CardPurchase; installments: CardInstallment[] }>(`/credit-cards/${cardId}/purchases`, { method: 'POST', body: purchase }),
    invoices: (cardId: string) => request<CardInvoice[]>(`/credit-cards/${cardId}/invoices`),
    invoice: (cardId: string, month: string) => request<CardInvoiceDetail>(`/credit-cards/${cardId}/invoices/${month}`),
    closeInvoice: (cardId: string, month: string) => request<CardInvoice>(`/credit-cards/${cardId}/invoices/${month}/close`, { method: 'POST' }),
    payInvoice: (cardId: string, month: string, paidAt: string) => request<CardInvoice>(`/credit-cards/${cardId}/invoices/${month}/pay`, { method: 'POST', body: { paid_at: paidAt } }),
  },
}

export async function downloadMonthlyReport(month: string) {
  const token=await accessToken()
  const response=await fetch(`/api/reports/monthly.csv?month=${encodeURIComponent(month)}`,{headers:{...(token?{Authorization:`Bearer ${token}`}:{})}})
  if(!response.ok)throw new Error('Não foi possível exportar o relatório.')
  return response.blob()
}
