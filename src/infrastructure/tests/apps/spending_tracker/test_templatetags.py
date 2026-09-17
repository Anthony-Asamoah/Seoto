from decimal import Decimal

from django.test import TestCase

from domains.apps.spending_tracker.templatetags.spending_extras import (
    comma_amount, humanize_amount,
)


class HumanizeAmountFilterTests(TestCase):
    """`humanize_amount` abbreviates large figures with K/M/B for compact display."""

    def test_below_thousand_keeps_two_decimals(self):
        self.assertEqual(humanize_amount(588), '588.00')
        self.assertEqual(humanize_amount(0), '0.00')

    def test_thousands_use_k_suffix(self):
        self.assertEqual(humanize_amount(7800), '7.8K')
        self.assertEqual(humanize_amount(6285.06), '6.29K')
        self.assertEqual(humanize_amount(1000), '1K')

    def test_millions_use_m_suffix(self):
        self.assertEqual(humanize_amount(2_300_000), '2.3M')

    def test_billions_use_b_suffix(self):
        self.assertEqual(humanize_amount(4_500_000_000), '4.5B')

    def test_negative_values_keep_sign(self):
        self.assertEqual(humanize_amount(-7800), '-7.8K')
        self.assertEqual(humanize_amount(-500), '-500.00')

    def test_non_numeric_input_returned_unchanged(self):
        self.assertEqual(humanize_amount('N/A'), 'N/A')
        self.assertEqual(humanize_amount(None), None)


class CommaAmountFilterTests(TestCase):
    """`comma_amount` renders full figures with thousands separators."""

    def test_groups_thousands(self):
        self.assertEqual(comma_amount(2000), '2,000.00')
        self.assertEqual(comma_amount(45999.5), '45,999.50')
        self.assertEqual(comma_amount(Decimal('1234567.891')), '1,234,567.89')

    def test_below_thousand_keeps_two_decimals(self):
        self.assertEqual(comma_amount(588), '588.00')
        self.assertEqual(comma_amount(0), '0.00')

    def test_negative_values_keep_sign(self):
        self.assertEqual(comma_amount(-7800), '-7,800.00')

    def test_non_numeric_input_returned_unchanged(self):
        self.assertEqual(comma_amount('N/A'), 'N/A')
        self.assertEqual(comma_amount(None), None)
