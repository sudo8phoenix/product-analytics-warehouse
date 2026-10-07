import json
import tempfile
import unittest
from pathlib import Path

from warehouse.analytics import channel_revenue, cohort_retention, funnel
from warehouse.pipeline import connect, ingest, quality


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_events.jsonl"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection = connect(Path(self.temp.name) / "warehouse.db")
        self.addCleanup(self.connection.close)

    def test_idempotent_rerun_and_metrics(self):
        first = ingest(self.connection, SAMPLE)
        before = quality(self.connection)
        second = ingest(self.connection, SAMPLE)
        self.assertEqual(first["inserted_events"], 23)
        self.assertEqual(second["inserted_events"], 0)
        self.assertEqual(second["updated_events"], 0)
        self.assertEqual(before, quality(self.connection))
        self.assertEqual(before["orders"], 3)
        self.assertEqual(before["revenue"], 230)
        self.assertEqual(before["anonymous_events"], 1)
        self.assertEqual(before["purchases_without_transaction"], 1)
        self.assertEqual([r["sessions"] for r in funnel(self.connection)], [8, 5, 4, 3])
        self.assertEqual(channel_revenue(self.connection)[0]["revenue"], 150)
        cohort = [r for r in cohort_retention(self.connection) if r["cohort_week"] == "2026-09-28" and r["week_number"] == 1]
        self.assertEqual(cohort[0]["retained_users"], 2)
        self.assertEqual(cohort[0]["cohort_users"], 5)

    def test_late_event_and_correction_are_upserts(self):
        ingest(self.connection, SAMPLE)
        path = Path(self.temp.name) / "late.jsonl"
        late = {"event_id": "e24", "event_timestamp": "2026-09-30T12:00:00Z", "ingested_at": "2026-10-08T12:00:00Z", "user_id": "u3", "session_id": "s3", "event_name": "begin_checkout"}
        path.write_text(json.dumps(late) + "\n")
        self.assertEqual(ingest(self.connection, path)["inserted_events"], 1)
        self.assertEqual(ingest(self.connection, path)["inserted_events"], 0)
        self.assertEqual([r["sessions"] for r in funnel(self.connection)], [8, 5, 5, 3])
        correction = {"event_id": "e21", "event_timestamp": "2026-10-07T14:06:00Z", "ingested_at": "2026-10-08T13:00:00Z", "user_id": "u6", "session_id": "s8", "event_name": "purchase", "transaction_id": "t3", "amount": 90}
        path.write_text(json.dumps(correction) + "\n")
        self.assertEqual(ingest(self.connection, path)["updated_events"], 1)
        self.assertEqual(quality(self.connection)["revenue"], 240)
        self.assertEqual(ingest(self.connection, path)["updated_events"], 0)

    def test_ordered_funnel_and_duplicate_transaction(self):
        ingest(self.connection, SAMPLE)
        path = Path(self.temp.name) / "extra.jsonl"
        records = [
            {"event_id": "e25", "event_timestamp": "2026-10-02T12:59:00Z", "ingested_at": "2026-10-08T12:00:00Z", "user_id": "u5", "session_id": "s5", "event_name": "add_to_cart"},
            {"event_id": "e26", "event_timestamp": "2026-10-02T13:01:00Z", "ingested_at": "2026-10-08T12:00:00Z", "user_id": "u5", "session_id": "s5", "event_name": "add_to_cart"},
            {"event_id": "e27", "event_timestamp": "2026-10-07T14:07:00Z", "ingested_at": "2026-10-08T12:00:00Z", "user_id": "u6", "session_id": "s8", "event_name": "purchase", "transaction_id": "t3", "amount": 80},
        ]
        path.write_text("\n".join(json.dumps(row) for row in records) + "\n")
        ingest(self.connection, path)
        self.assertEqual([r["sessions"] for r in funnel(self.connection)], [8, 6, 5, 3])
        self.assertEqual(quality(self.connection)["orders"], 3)
        self.assertEqual(quality(self.connection)["revenue"], 230)


if __name__ == "__main__":
    unittest.main()
