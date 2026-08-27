import type { Account, AccountCreate, Category, CategoryBudget, CategoryWrite, DashboardMetrics, Health, Transaction, TransactionCreate } from './types'

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
  accounts: {
    list: () => request<Account[]>('/accounts'),
    create: (account: AccountCreate) => request<Account>('/accounts', { method: 'POST', body: account }),
    updateBalance: (accountId: string, value: number) => request<Account>(`/accounts/${accountId}/balance`, { method: 'PATCH', body: { value } }),
    updateMonthlyIncome: (accountId: string, value: number) => request<Account>(`/accounts/${accountId}/monthly-income`, { method: 'PATCH', body: { value } }),
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
    delete: (transactionId: string) => request<void>(`/transactions/${transactionId}`, { method: 'DELETE' }),
    deleteSeries: (groupId: string) => request<void>(`/transaction-series/${groupId}`, { method: 'DELETE' }),
  },
}
