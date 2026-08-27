import type { Account, AccountCreate, Category, CategoryBudget, CategoryWrite, DashboardMetrics, ExpenseOccurrence, Health, RecurringExpense, RecurringExpenseWrite, ScheduledIncome, Transaction, TransactionCreate, TransactionUpdate } from './types'

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: options.method ?? 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
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
}
