import unittest

from backend.application.services import CategoryService, SaveCategoryRequest
from backend.domain import Money, TransactionType
from backend.infrastructure import JsonUnitOfWork


class CategoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": []}
        self.commits = 0
        self.service = CategoryService(JsonUnitOfWork(self.data, self._persist))

    def _persist(self):
        self.commits += 1

    @staticmethod
    def _request(name="Mercado", monthly_limit="300"):
        return SaveCategoryRequest(
            name=name,
            category_type=TransactionType.EXPENSE,
            monthly_limit=Money.from_value(monthly_limit),
        )

    def test_same_normalized_name_and_type_updates_existing_category(self):
        category = self.service.create_or_update(self._request())
        updated = self.service.create_or_update(
            self._request("  mercado  ", "450")
        )

        self.assertEqual(category.id, updated.id)
        self.assertEqual(1, len(self.data["categories"]))
        self.assertEqual(Money.from_value("450"), updated.monthly_limit)

    def test_update_missing_category_returns_none_without_persisting(self):
        result = self.service.update("missing", self._request())

        self.assertIsNone(result)
        self.assertEqual(0, self.commits)

    def test_delete_keeps_legacy_idempotent_contract(self):
        self.assertTrue(self.service.delete("missing"))
        self.assertEqual(0, self.commits)
