import unittest
from datetime import date

from backend.application.services import MonthlyReportService
from backend.domain import CardInstallment, Category, CreditCard, Money, Transaction, TransactionType
from backend.infrastructure import JsonUnitOfWork


class MonthlyReportServiceTests(unittest.TestCase):
    def test_consolidates_bank_and_card_expenses_by_category(self):
        data={"accounts":[],"categories":[],"transactions":[]}
        uow=JsonUnitOfWork(data,lambda:None)
        uow.categories.save(Category("food","Alimentação",TransactionType.EXPENSE))
        uow.transactions.save(Transaction("income",Money.from_value("2000"),date(2026,8,2),"salary","account","Salário",TransactionType.INCOME))
        uow.transactions.save(Transaction("expense",Money.from_value("150"),date(2026,8,3),"food","account","Mercado",TransactionType.EXPENSE))
        uow.credit_cards.save(CreditCard("card","Roxo",Money.from_value("1000"),20,28,"account"))
        uow.card_installments.save_all([CardInstallment("part","purchase","card","food","Compra",Money.from_value("100"),1,2,date(2026,8,1))])
        report=MonthlyReportService(uow).get_month(date(2026,8,27))
        self.assertEqual(Money.from_value("2000"),report.income)
        self.assertEqual(Money.from_value("150"),report.bank_expenses)
        self.assertEqual(Money.from_value("100"),report.card_expenses)
        self.assertEqual(Money.from_value("1750"),report.result)
        self.assertEqual(Money.from_value("250"),report.categories[0].total)


if __name__=="__main__":unittest.main()
