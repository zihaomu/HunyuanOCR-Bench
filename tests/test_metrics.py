import unittest

from hunyuanocr_bench.metrics import component_overall, normalize_accuracy


class AccuracyMetricTests(unittest.TestCase):
    def test_paper_table_12_hunyuanocr_15_row(self) -> None:
        metrics = normalize_accuracy(
            {
                "Overall": 94.74,
                "TextEdit": 0.039,
                "FormulaCDM": 94.50,
                "TableTEDS": 93.67,
                "TableTEDS_S": 94.71,
                "OrderEdit": 0.129,
            }
        )

        self.assertEqual(metrics.overall, 94.74)
        self.assertEqual(metrics.order_edit, 0.129)
        self.assertAlmostEqual(
            component_overall(
                metrics.text_edit,
                metrics.formula_cdm,
                metrics.table_teds,
            ),
            94.75666666666666,
        )

    def test_paper_table_12_hunyuanocr_10_row_disambiguates_overall(self) -> None:
        metrics = normalize_accuracy(
            {
                "Overall": 92.03,
                "TextEdit": 0.048,
                "FormulaCDM": 88.60,
                "TableTEDS": 92.37,
                "TableTEDS_S": 93.99,
                "OrderEdit": 0.138,
            }
        )

        self.assertEqual(metrics.overall, 92.03)
        self.assertAlmostEqual(
            component_overall(
                metrics.text_edit,
                metrics.formula_cdm,
                metrics.table_teds,
            ),
            92.05666666666667,
        )

    def test_evaluator_fraction_scores_are_converted_to_percent(self) -> None:
        metrics = normalize_accuracy(
            {
                "Overall": 0.75,
                "Text Edit Distance": 0.10,
                "Formula CDM": 0.70,
                "Table TEDS": 0.65,
                "Table TEDS Structure Only": 0.75,
                "Reading Order Edit Distance": 0.20,
            }
        )

        self.assertEqual(metrics.formula_cdm, 70.0)
        self.assertEqual(metrics.overall, 75.0)

    def test_inconsistent_overall_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "disagrees"):
            normalize_accuracy(
                {
                    "Overall": 10.0,
                    "TextEdit": 0.039,
                    "FormulaCDM": 94.50,
                    "TableTEDS": 93.67,
                    "TableTEDS_S": 94.71,
                    "OrderEdit": 0.129,
                }
            )


if __name__ == "__main__":
    unittest.main()
