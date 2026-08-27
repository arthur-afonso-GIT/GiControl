import { describe, expect, it } from 'vitest'
import type { Account, Transaction } from '../../api/types'
import { buildExpenseForecast } from './forecast'

const accounts: Account[] = [
  { id: 'checking', name: 'Conta principal', type: 'Conta Corrente', balance: 1000, monthly_income: 2000 },
  { id: 'card', name: 'Cartão', type: 'Cartão', balance: 0, monthly_income: 0 },
]

function transaction(id: string, amount: number, date: string, accountId: string, type: 'Receita' | 'Despesa' = 'Despesa'): Transaction {
  return { id, amount, date, account_id: accountId, category_id: 'category', description: id, type, is_fixed: false }
}

describe('buildExpenseForecast', () => {
  it('agrupa despesas por conta e ordena a maior participação primeiro', () => {
    const result = buildExpenseForecast([
      transaction('market', 300, '2026-08-05', 'checking'),
      transaction('internet', 100, '2026-08-10', 'checking'),
      transaction('card', 600, '2026-08-12', 'card'),
      transaction('salary', 5000, '2026-08-01', 'checking', 'Receita'),
    ], accounts, '2026-08', 1)

    expect(result[0].total).toBe(1000)
    expect(result[0].accounts.map((item) => item.accountName)).toEqual(['Cartão', 'Conta principal'])
    expect(result[0].accounts.map((item) => item.percentage)).toEqual([60, 40])
  })

  it('contabiliza cada parcela no respectivo mês e atravessa a virada do ano', () => {
    const result = buildExpenseForecast([
      transaction('phone (1/3)', 100, '2026-12-20', 'card'),
      transaction('phone (2/3)', 100, '2027-01-20', 'card'),
      transaction('phone (3/3)', 100, '2027-02-20', 'card'),
    ], accounts, '2026-12', 3)

    expect(result.map((item) => item.month)).toEqual(['2026-12', '2027-01', '2027-02'])
    expect(result.map((item) => item.total)).toEqual([100, 100, 100])
  })

  it('mantém meses vazios e identifica contas removidas', () => {
    const result = buildExpenseForecast([
      transaction('orphan', 25, '2026-09-02', 'removed'),
    ], accounts, '2026-08', 2)

    expect(result[0].accounts).toEqual([])
    expect(result[1].accounts[0].accountName).toBe('Conta removida')
  })
})
