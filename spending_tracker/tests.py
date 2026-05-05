from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Account, Category, Transaction


class InfiniteScrollPartialTests(TestCase):
    """Tests for infinite-scroll partial fragment endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='scrolluser', password='pass')
        cls.account = Account.objects.create(
            name='Main', user=cls.user, balance=Decimal('1000000.00')
        )
        cls.expense_category = Category.objects.create(label='groceries', user=cls.user)
        # Create 25 transactions: alternating income/expense to exercise filters
        for i in range(25):
            mode = 'INCOME' if i % 2 == 0 else 'EXPENSE'
            Transaction.objects.create(
                mode=mode,
                amount=Decimal('10.00'),
                currency='GHS',
                account=cls.account,
                category=cls.expense_category if mode == 'EXPENSE' else None,
            )

    def setUp(self):
        self.client.force_login(self.user)

    def _assert_fragment(self, response, expect_has_next):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Has-Next'], '1' if expect_has_next else '0')
        self.assertNotIn(b'<html', response.content)
        self.assertNotIn(b'<!DOCTYPE', response.content)

    def test_transaction_list_flat_partial_honors_filter(self):
        url = reverse('spending_tracker:transaction_list')
        res = self.client.get(url, {'partial': '1', 'page': '1', 'mode': 'EXPENSE'})
        self._assert_fragment(res, expect_has_next=True)
        # 12 EXPENSE transactions / 10 per page → page 2 is last
        res2 = self.client.get(url, {'partial': '1', 'page': '2', 'mode': 'EXPENSE'})
        self._assert_fragment(res2, expect_has_next=False)

    def test_transaction_list_grouped_partial(self):
        url = reverse('spending_tracker:transaction_list')
        res = self.client.get(url, {'partial': '1', 'page': '1', 'group_by': 'day'})
        self._assert_fragment(res, expect_has_next=False)
        # Grouped fragment renders group label container markup
        self.assertIn(b'fw-semibold', res.content)

    def test_account_detail_partial(self):
        url = reverse('spending_tracker:account_detail', args=[self.account.id])
        res = self.client.get(url, {'partial': '1', 'page': '1'})
        self._assert_fragment(res, expect_has_next=True)
        res_last = self.client.get(url, {'partial': '1', 'page': '3'})
        self._assert_fragment(res_last, expect_has_next=False)

