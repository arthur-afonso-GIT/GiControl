import unittest

from backend.application.ports import CategoryRepository
from backend.domain import Category, Money, TransactionType
from backend.infrastructure.repositories import JsonCategoryRepository


class JsonCategoryRepositoryContractTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "id": "food",
                "name": "Alimentação",
                "type": "Despesa",
                "monthly_limit": 500.0,
            }
        ]
        self.persist_calls = 0
        self.repository = JsonCategoryRepository(self.records, self._persist)

    def _persist(self):
        self.persist_calls += 1

    def test_adapter_satisfies_repository_protocol(self):
        repository: CategoryRepository = self.repository

        self.assertEqual("food", repository.list_all()[0].id)

    def test_maps_legacy_record_to_domain(self):
        category = self.repository.get("food")

        self.assertIsNotNone(category)
        self.assertEqual(TransactionType.EXPENSE, category.category_type)
        self.assertEqual(Money.from_value("500"), category.monthly_limit)

    def test_missing_monthly_limit_defaults_to_zero(self):
        self.records[0].pop("monthly_limit")

        category = self.repository.get("food")

        self.assertEqual(Money.zero(), category.monthly_limit)

    def test_save_updates_existing_record_and_persists(self):
        category = Category(
            id="food",
            name="Mercado",
            category_type=TransactionType.EXPENSE,
            monthly_limit=Money.from_value("650"),
        )

        self.repository.save(category)

        self.assertEqual(1, len(self.records))
        self.assertEqual("Mercado", self.records[0]["name"])
        self.assertEqual(650.0, self.records[0]["monthly_limit"])
        self.assertEqual(1, self.persist_calls)

    def test_save_appends_new_record_and_persists(self):
        category = Category(
            id="salary",
            name="Salário",
            category_type=TransactionType.INCOME,
        )

        self.repository.save(category)

        self.assertEqual(2, len(self.records))
        self.assertEqual("Receita", self.records[1]["type"])
        self.assertEqual(1, self.persist_calls)

    def test_delete_existing_record_persists(self):
        self.assertTrue(self.repository.delete("food"))

        self.assertEqual([], self.records)
        self.assertEqual(1, self.persist_calls)

    def test_delete_missing_record_does_not_persist(self):
        self.assertFalse(self.repository.delete("missing"))

        self.assertEqual(1, len(self.records))
        self.assertEqual(0, self.persist_calls)


if __name__ == "__main__":
    unittest.main()
