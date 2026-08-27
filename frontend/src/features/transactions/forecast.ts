import type { Account, Transaction } from '../../api/types'

export type AccountExpenseForecast = { accountId: string; accountName: string; amount: number; percentage: number }
export type MonthlyExpenseForecast = { month: string; label: string; total: number; accounts: AccountExpenseForecast[] }

export function buildExpenseForecast(transactions: Transaction[], accounts: Account[], startMonth: string, numberOfMonths = 6): MonthlyExpenseForecast[] {
  const [year, month] = startMonth.split('-').map(Number)

  return Array.from({ length: numberOfMonths }, (_, index) => {
    const date = new Date(year, month - 1 + index, 1)
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    const totals = new Map<string, number>()

    transactions.filter((transaction) => transaction.type === 'Despesa' && transaction.date.startsWith(monthKey))
      .forEach((transaction) => totals.set(transaction.account_id, (totals.get(transaction.account_id) ?? 0) + transaction.amount))

    const total = [...totals.values()].reduce((sum, amount) => sum + amount, 0)
    const accountNames = new Map(accounts.map((account) => [account.id, account.name]))
    const groupedAccounts = [...totals.entries()].map(([accountId, amount]) => ({
      accountId,
      accountName: accountNames.get(accountId) ?? 'Conta removida',
      amount,
      percentage: total ? amount / total * 100 : 0,
    })).sort((a, b) => b.amount - a.amount)

    return {
      month: monthKey,
      label: new Intl.DateTimeFormat('pt-BR', { month: 'short', year: '2-digit' }).format(date).replace('.', ''),
      total,
      accounts: groupedAccounts,
    }
  })
}
