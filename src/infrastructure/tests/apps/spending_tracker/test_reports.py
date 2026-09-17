from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from domains.apps.spending_tracker.models import Account, Category, Transaction


class AccountReportCardTests(TestCase):
    """Per-account report cards: balance series, flows and derived metrics."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='reportuser', password='pass')
        cls.checking = Account.objects.create(
            name='Checking', user=cls.user, account_type='CHECKING', balance=Decimal('900.00')
        )
        cls.savings = Account.objects.create(
            name='Savings', user=cls.user, account_type='SAVINGS', balance=Decimal('1200.00')
        )
        cls.groceries = Category.objects.create(label='groceries', user=cls.user)

        now = timezone.now()
        # Keep everything inside "this month" so the month period picks it up.
        base = now.replace(day=1, hour=0, minute=5, second=0, microsecond=0)
        Transaction.objects.create(
            mode='INCOME', amount=Decimal('500.00'), currency='GHS',
            account=cls.checking, transaction_time=base,
        )
        Transaction.objects.create(
            mode='EXPENSE', amount=Decimal('300.00'), currency='GHS',
            account=cls.checking, category=cls.groceries,
            transaction_time=base + timedelta(minutes=10),
        )
        Transaction.objects.create(
            mode='TRANSFER', amount=Decimal('200.00'), currency='GHS',
            account=cls.checking, destination_account=cls.savings,
            transaction_time=base + timedelta(minutes=20),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _rows(self, **params):
        res = self.client.get(reverse('spending_tracker:reports'), params)
        self.assertEqual(res.status_code, 200)
        return res, {row['account'].name: row for row in res.context['account_performance']}

    def test_net_change_and_opening_balance_reconcile(self):
        _res, rows = self._rows(period='month', modifier='this')
        checking = rows['Checking']
        # +500 income, -300 expense, -200 transfer out = 0 net
        self.assertEqual(checking['net_change'], 0)
        self.assertEqual(checking['starting_balance'], Decimal('900.00'))
        self.assertEqual(checking['income'], Decimal('500.00'))
        self.assertEqual(checking['expenses'], Decimal('300.00'))
        self.assertEqual(checking['transfers_out'], Decimal('200.00'))

        savings = rows['Savings']
        self.assertEqual(savings['transfers_in'], Decimal('200.00'))
        self.assertEqual(savings['net_change'], Decimal('200.00'))
        # Transaction.save() already credited the transfer, so the live balance is
        # 1400 and the opening balance backs the movement out again.
        self.assertEqual(savings['current_balance'], Decimal('1400.00'))
        self.assertEqual(savings['starting_balance'], Decimal('1200.00'))

    def test_balance_series_ends_at_current_balance(self):
        _res, rows = self._rows(period='month', modifier='this')
        for name, row in rows.items():
            self.assertTrue(row['series'], f'{name} has no balance series')
            self.assertAlmostEqual(
                row['series'][-1], float(row['current_balance']), places=2,
                msg=f'{name} series does not close on the current balance',
            )

    def test_top_expense_category_reported_per_account(self):
        _res, rows = self._rows(period='month', modifier='this')
        self.assertEqual(rows['Checking']['top_category']['label'], 'groceries')
        self.assertEqual(rows['Checking']['top_category']['total'], 300.0)
        self.assertIsNone(rows['Savings']['top_category'])

    def test_account_filter_limits_cards_to_that_account(self):
        _res, rows = self._rows(period='month', modifier='this', account=self.savings.id)
        self.assertEqual(list(rows), ['Savings'])

    def test_chart_payload_matches_labels_and_series_length(self):
        res, _rows = self._rows(period='month', modifier='this')
        payload = res.context['json_account_performance']
        self.assertEqual(len(payload), 2)
        for entry in payload:
            self.assertEqual(len(entry['labels']), len(entry['series']))
            self.assertNotIn('accountPerformanceChart', res.content.decode())


class TransferRouteReportTests(TestCase):
    """Transfer activity presented as source → destination route cards."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='routeuser', password='pass')
        cls.checking = Account.objects.create(
            name='Checking', user=cls.user, account_type='CHECKING', balance=Decimal('5000.00')
        )
        cls.savings = Account.objects.create(
            name='Savings', user=cls.user, account_type='SAVINGS', balance=Decimal('0.00')
        )
        cls.cash = Account.objects.create(
            name='Cash', user=cls.user, account_type='CASH', balance=Decimal('0.00')
        )

        base = timezone.now().replace(day=1, hour=0, minute=5, second=0, microsecond=0)
        for offset, amount in ((0, '300.00'), (10, '500.00')):
            Transaction.objects.create(
                mode='TRANSFER', amount=Decimal(amount), currency='GHS',
                account=cls.checking, destination_account=cls.savings,
                transaction_time=base + timedelta(minutes=offset),
            )
        Transaction.objects.create(
            mode='TRANSFER', amount=Decimal('200.00'), currency='GHS',
            account=cls.checking, destination_account=cls.cash,
            transaction_time=base + timedelta(minutes=20),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _routes(self):
        res = self.client.get(
            reverse('spending_tracker:reports'), {'period': 'month', 'modifier': 'this'}
        )
        self.assertEqual(res.status_code, 200)
        return res, {(r['source'], r['destination']): r for r in res.context['transfer_routes']}

    def test_routes_group_by_source_and_destination_pair(self):
        _res, routes = self._routes()
        self.assertEqual(set(routes), {('Checking', 'Savings'), ('Checking', 'Cash')})

        to_savings = routes[('Checking', 'Savings')]
        self.assertEqual(to_savings['count'], 2)
        self.assertEqual(to_savings['volume'], 800.0)
        self.assertEqual(to_savings['avg_amount'], 400.0)
        self.assertEqual(to_savings['largest'], 500.0)

    def test_route_shares_sum_to_full_volume(self):
        res, routes = self._routes()
        self.assertEqual(res.context['total_transfer_volume'], 1000.0)
        self.assertEqual(routes[('Checking', 'Savings')]['share'], 80.0)
        self.assertEqual(routes[('Checking', 'Cash')]['share'], 20.0)

    def test_route_series_matches_bucket_labels_and_totals(self):
        res, routes = self._routes()
        payload = res.context['json_transfer_routes']
        self.assertEqual(len(payload), len(routes))
        for entry in payload:
            self.assertEqual(len(entry['labels']), len(entry['series']))
        for route in routes.values():
            self.assertAlmostEqual(sum(route['series']), route['volume'], places=2)

    def test_transfer_without_destination_is_flagged(self):
        Transaction.objects.create(
            mode='TRANSFER', amount=Decimal('50.00'), currency='GHS',
            account=self.checking, destination_account=None,
            transaction_time=timezone.now().replace(day=1, hour=1, minute=0, second=0, microsecond=0),
        )
        _res, routes = self._routes()
        orphan = routes[('Checking', 'Unspecified')]
        self.assertFalse(orphan['has_destination'])
        self.assertEqual(orphan['count'], 1)


class CategoryBarChartContextTests(TestCase):
    """Top income/expense cards render as bar charts fed by JSON payloads."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='baruser', password='pass')
        cls.account = Account.objects.create(name='Main', user=cls.user, balance=Decimal('500.00'))
        cls.salary = Category.objects.create(label='salary', user=cls.user)
        cls.rent = Category.objects.create(label='rent', user=cls.user)

        base = timezone.now().replace(day=1, hour=0, minute=5, second=0, microsecond=0)
        Transaction.objects.create(
            mode='INCOME', amount=Decimal('900.00'), currency='GHS', account=cls.account,
            category=cls.salary, transaction_time=base,
        )
        Transaction.objects.create(
            mode='EXPENSE', amount=Decimal('400.00'), currency='GHS', account=cls.account,
            category=cls.rent, transaction_time=base + timedelta(minutes=5),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_income_and_expense_payloads_present(self):
        res = self.client.get(
            reverse('spending_tracker:reports'), {'period': 'month', 'modifier': 'this'}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.context['json_income_categories'],
            [{'label': 'salary', 'total': 900.0, 'count': 1}],
        )
        self.assertEqual(
            res.context['json_expense_categories'],
            [{'label': 'rent', 'total': 400.0, 'count': 1}],
        )
        content = res.content.decode()
        self.assertIn('incomeCategoryBarChart', content)
        self.assertIn('expenseCategoryBarChart', content)
