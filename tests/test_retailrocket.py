import tempfile
import unittest
from pathlib import Path

from warehouse.retailrocket import load_csv, visitor_funnel, weekly_return
from warehouse.pipeline import connect


class RetailrocketTests(unittest.TestCase):
    def test_real_source_format_load_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "events.csv"
            db_path = Path(temp) / "warehouse.db"
            csv_path.write_text(
                "timestamp,visitorid,event,itemid,transactionid\n"
                "1439694000000,1,view,100,\n"
                "1439694060000,1,addtocart,100,\n"
                "1439694120000,1,transaction,100,234\n"
                "1439694120000,1,transaction,101,234\n"
            )
            first = load_csv(csv_path, db_path)
            second = load_csv(csv_path, db_path)
            self.assertEqual(first["inserted_events"], 4)
            self.assertEqual(first["orders"], 1)
            self.assertEqual(second["inserted_events"], 0)
            connection = connect(db_path)
            self.assertEqual([r["visitors"] for r in visitor_funnel(connection)], [1, 1, 1])
            self.assertEqual(weekly_return(connection)[0]["returned_users"], 0)
            connection.close()


if __name__ == "__main__":
    unittest.main()
