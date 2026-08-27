import unittest
from backend.infrastructure.migrate_legacy_to_user import schema_for

class LegacyUserMigrationTests(unittest.TestCase):
    def test_user_id_becomes_safe_private_schema(self):
        self.assertEqual("user_12345678_1234_1234_1234_123456789abc",schema_for("12345678-1234-1234-1234-123456789abc"))
    def test_invalid_identifier_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"inválido"):schema_for("public; drop schema public")

if __name__=="__main__":unittest.main()
