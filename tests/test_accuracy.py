import unittest

from hunyuanocr_bench.accuracy import extract_metric_result, extract_run_summary


class AccuracyParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = {
            "text_block": {"all": {"Edit_dist": {"ALL_page_avg": 0.039}}},
            "display_formula": {"page": {"CDM": {"ALL": 0.945}}},
            "table": {
                "page": {
                    "TEDS": {"ALL": 0.9367},
                    "TEDS_structure_only": {"ALL": 0.9471},
                }
            },
            "reading_order": {"all": {"Edit_dist": {"ALL_page_avg": 0.129}}},
        }

    def test_extract_official_metric_result(self) -> None:
        metrics = extract_metric_result(self.raw)
        self.assertAlmostEqual(metrics["overall"], 94.75666666666666)
        self.assertAlmostEqual(metrics["table_teds_s"], 94.71)

    def test_extract_official_run_summary(self) -> None:
        payload = {
            "notebook_metric_summary": {
                "overall_notebook": 94.75666666666666,
                "metrics": {
                    "text_block_Edit_dist": {"notebook_value": 0.039},
                    "display_formula_CDM": {"notebook_value": 94.5},
                    "table_TEDS": {"notebook_value": 93.67},
                    "table_TEDS_structure_only": {"notebook_value": 94.71},
                    "reading_order_Edit_dist": {"notebook_value": 0.129},
                },
            }
        }
        self.assertEqual(extract_run_summary(payload)["formula_cdm"], 94.5)


if __name__ == "__main__":
    unittest.main()
