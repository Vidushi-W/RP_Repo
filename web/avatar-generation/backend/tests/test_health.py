import unittest
from app.api.routes import health
class HealthTests(unittest.TestCase):
    def test_health_does_not_claim_pipeline_readiness(self):
        self.assertEqual(health(), {"status": "ok", "pipeline": "not_implemented"})
if __name__ == "__main__":
    unittest.main()
