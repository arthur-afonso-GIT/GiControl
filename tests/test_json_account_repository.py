import unittest

from backend.application.ports import AccountRepository
from backend.domain import Account, AccountType, Money
from backend.infrastructure.repositories import JsonAccountRepository


class JsonAccountRepositoryContractTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "id": "main",
                "name": "Conta principal",
                "type": "Conta Corrente",
                "balance": 100.0,
                "monthly_income": 1500.0,
            }
        ]
        self.persist_calls = 0
        self.repository = JsonAccountRepository(self.records, self._persist)

    def _persist(self):
        self.persist_calls += 1

    def test_adapter_satisfies_repository_protocol(self):
        repository: AccountRepository = self.repository

        self.assertEqual("main", repository.list_all()[0].id)

    def test_maps_legacy_record_to_domain(self):
        account = self.repository.get("main")

        self.assertIsNotNone(account)
        self.assertEqual(AccountType.CHECKING, account.account_type)
        self.assertEqual(Money.from_value("100"), account.balance)
        self.assertEqual(Money.from_value("1500"), account.monthly_income)

    def test_missing_monthly_income_defaults_to_zero(self):
        self.records[0].pop("monthly_income")

        account = self.repository.get("main")

        self.assertEqual(Money.zero(), account.monthly_income)

    def test_save_updates_record_in_place_and_persists(self):
        original_record = self.records[0]
        account = Account(
            id="main",
            name="Conta atualizada",
            account_type=AccountType.CHECKING,
            balance=Money.from_value("250.50"),
            monthly_income=Money.from_value("1800"),
        )

        self.repository.save(account)

        self.assertIs(original_record, self.records[0])
        self.assertEqual(250.5, original_record["balance"])
        self.assertEqual(1, self.persist_calls)

    def test_save_appends_new_record(self):
        account = Account(
            id="wallet",
            name="Carteira",
            account_type=AccountType.WALLET,
            balance=Money.from_value("20"),
        )

        self.repository.save(account)

        self.assertEqual(2, len(self.records))
        self.assertEqual("Carteira", self.records[1]["type"])
        self.assertEqual(1, self.persist_calls)

    def test_delete_existing_record_persists(self):
        self.assertTrue(self.repository.delete("main"))

        self.assertEqual([], self.records)
        self.assertEqual(1, self.persist_calls)

    def test_delete_missing_record_does_not_persist(self):
        self.assertFalse(self.repository.delete("missing"))

        self.assertEqual(1, len(self.records))
        self.assertEqual(0, self.persist_calls)


if __name__ == "__main__":
    unittest.main()
