from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Account, Category, Transaction, RecurringTransaction, RecurringTransactionOccurrence,
    RecurringFrequencyChoices, CustomRecurrenceTypeChoices, RecurringOccurrenceStatusChoices,
)
from .services import process_due_occurrences


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


class RecurringTransactionNextOccurrenceTests(TestCase):
    """Unit tests for RecurringTransaction.next_occurrence() — no DB save needed."""

    def _schedule(self, **kwargs):
        return RecurringTransaction(mode='EXPENSE', amount=Decimal('10.00'), **kwargs)

    def test_daily(self):
        schedule = self._schedule(frequency=RecurringFrequencyChoices.DAILY)
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 10)), date(2026, 1, 11))

    def test_weekly(self):
        schedule = self._schedule(frequency=RecurringFrequencyChoices.WEEKLY)
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 10)), date(2026, 1, 17))

    def test_monthly_clamps_short_month(self):
        schedule = self._schedule(frequency=RecurringFrequencyChoices.MONTHLY)
        # Jan 31 -> Feb has only 28 days in 2026 (not a leap year)
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 31)), date(2026, 2, 28))

    def test_quarterly(self):
        schedule = self._schedule(frequency=RecurringFrequencyChoices.QUARTERLY)
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 31)), date(2026, 4, 30))

    def test_yearly_leap_day_clamps(self):
        schedule = self._schedule(frequency=RecurringFrequencyChoices.YEARLY)
        # Feb 29 2024 (leap) -> 2025 is not a leap year
        self.assertEqual(schedule.next_occurrence(date(2024, 2, 29)), date(2025, 2, 28))

    def test_custom_days_of_week_wraps_to_next_week(self):
        schedule = self._schedule(
            frequency=RecurringFrequencyChoices.CUSTOM,
            custom_type=CustomRecurrenceTypeChoices.DAYS_OF_WEEK,
            custom_weekdays=[0, 3],  # Monday, Thursday
        )
        # 2026-01-10 is a Saturday; next Monday is 2026-01-12
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 10)), date(2026, 1, 12))
        # From that Monday, next hit is Thursday the same week
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 12)), date(2026, 1, 15))

    def test_custom_days_of_month_clamps_and_dedups_short_month(self):
        schedule = self._schedule(
            frequency=RecurringFrequencyChoices.CUSTOM,
            custom_type=CustomRecurrenceTypeChoices.DAYS_OF_MONTH,
            custom_month_days=[1, 30, 31],
        )
        # From Jan 15, next hit within January (31 days, no clamping needed) is Jan 30
        self.assertEqual(schedule.next_occurrence(date(2026, 1, 15)), date(2026, 1, 30))
        # From Feb 1, days 30 and 31 both clamp to Feb 28 (Feb 2026 has 28 days) and dedupe to one hit
        self.assertEqual(schedule.next_occurrence(date(2026, 2, 1)), date(2026, 2, 28))

    def test_advance_next_run_date_deactivates_past_end_date(self):
        schedule = self._schedule(
            frequency=RecurringFrequencyChoices.DAILY,
            next_run_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
            is_active=True,
        )
        schedule.advance_next_run_date()
        self.assertFalse(schedule.is_active)


class ProcessDueOccurrencesTests(TestCase):
    """Tests for the shared spending_tracker.services.process_due_occurrences engine."""

    def setUp(self):
        self.user = User.objects.create_user(username='recurringuser', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('1000.00'))
        self.today = date(2026, 6, 1)

    def _schedule(self, **kwargs):
        defaults = dict(
            user=self.user,
            mode='EXPENSE',
            amount=Decimal('50.00'),
            currency='GHS',
            account=self.account,
            frequency=RecurringFrequencyChoices.DAILY,
            renewal_date=self.today,
        )
        defaults.update(kwargs)
        return RecurringTransaction.objects.create(**defaults)

    def test_auto_renew_creates_transaction_and_updates_balance(self):
        schedule = self._schedule(is_auto_renew=True)
        process_due_occurrences(schedule, today=self.today)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('950.00'))

        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=schedule, scheduled_date=self.today)
        self.assertEqual(occurrence.status, RecurringOccurrenceStatusChoices.AUTO_CREATED)
        self.assertIsNotNone(occurrence.transaction)

        schedule.refresh_from_db()
        self.assertEqual(schedule.next_run_date, self.today + timedelta(days=1))

    def test_manual_creates_pending_occurrence_no_transaction(self):
        schedule = self._schedule(is_auto_renew=False)
        process_due_occurrences(schedule, today=self.today)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000.00'))

        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=schedule, scheduled_date=self.today)
        self.assertEqual(occurrence.status, RecurringOccurrenceStatusChoices.PENDING)
        self.assertIsNone(occurrence.transaction)

    def test_idempotent_when_run_twice_same_day(self):
        schedule = self._schedule(is_auto_renew=True)
        process_due_occurrences(schedule, today=self.today)
        schedule.refresh_from_db()
        # Simulate the daily command running again after next_run_date already advanced past today
        process_due_occurrences(schedule, today=self.today)

        self.assertEqual(RecurringTransactionOccurrence.objects.filter(recurring_transaction=schedule).count(), 1)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('950.00'))

    def test_paused_schedule_is_not_processed(self):
        schedule = self._schedule(is_auto_renew=True, is_active=False)
        process_due_occurrences(schedule, today=self.today)
        self.assertEqual(RecurringTransactionOccurrence.objects.filter(recurring_transaction=schedule).count(), 0)

    def test_end_date_deactivates_after_last_occurrence(self):
        schedule = self._schedule(is_auto_renew=True, end_date=self.today)
        process_due_occurrences(schedule, today=self.today)

        schedule.refresh_from_db()
        self.assertFalse(schedule.is_active)
        self.assertEqual(RecurringTransactionOccurrence.objects.filter(recurring_transaction=schedule).count(), 1)


class AddRecurringTransactionViewTests(TestCase):
    """Tests for scheduling a recurring transaction via the main Add Transaction form
    (the 'Make this a recurring transaction' checkbox)."""

    def setUp(self):
        self.user = User.objects.create_user(username='modaluser', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('500.00'))
        self.client.force_login(self.user)

    def _add_transaction_url(self):
        return f"{reverse('spending_tracker:add_transaction')}?mode=EXPENSE"

    def _get_idempotency_token(self):
        response = self.client.get(self._add_transaction_url())
        return response.context['idempotency_token']

    def _post_data(self, **overrides):
        today = date.today()
        data = {
            'mode': 'EXPENSE',
            'amount': '25.00',
            'currency': 'GHS',
            'account': str(self.account.pk),
            'category': '',
            'details': 'Netflix',
            'reference': '',
            'tags_input': '',
            'transaction_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'is_recurring': 'true',
            'frequency': 'DAILY',
            'renewal_date': today.isoformat(),
            'end_date': '',
            'idempotency_token': self._get_idempotency_token(),
        }
        data.update(overrides)
        return data

    def test_renewal_date_today_processes_immediately_when_auto_renew(self):
        response = self.client.post(self._add_transaction_url(), self._post_data(is_auto_renew='true'))
        self.assertRedirects(response, reverse('spending_tracker:recurring_list'))

        schedule = RecurringTransaction.objects.get(user=self.user)
        self.assertEqual(
            RecurringTransactionOccurrence.objects.filter(
                recurring_transaction=schedule, status=RecurringOccurrenceStatusChoices.AUTO_CREATED
            ).count(),
            1,
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('475.00'))

    def test_renewal_date_today_sends_pending_approval_when_not_auto_renew(self):
        response = self.client.post(self._add_transaction_url(), self._post_data())
        self.assertRedirects(response, reverse('spending_tracker:recurring_list'))

        schedule = RecurringTransaction.objects.get(user=self.user)
        self.assertEqual(
            RecurringTransactionOccurrence.objects.filter(
                recurring_transaction=schedule, status=RecurringOccurrenceStatusChoices.PENDING
            ).count(),
            1,
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('500.00'))

    def test_unchecked_is_recurring_creates_one_off_transaction(self):
        data = self._post_data()
        data.pop('is_recurring')
        data.pop('frequency')
        data.pop('renewal_date')
        data.pop('end_date')
        response = self.client.post(self._add_transaction_url(), data)
        self.assertRedirects(response, reverse('spending_tracker:transaction_list'))

        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Transaction.objects.filter(account=self.account).count(), 1)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('475.00'))

    def test_custom_frequency_with_weekdays(self):
        data = self._post_data(
            frequency='CUSTOM',
            custom_type='DAYS_OF_WEEK',
            is_auto_renew='true',
        )
        response = self.client.post(self._add_transaction_url(), data)
        # No weekday selected -> validation error, redisplays the form
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecurringTransaction.objects.filter(user=self.user).count(), 0)


class EditRecurringTransactionViewTests(TestCase):
    """Tests for editing a recurring transaction schedule — changes should only affect future runs."""

    def setUp(self):
        self.user = User.objects.create_user(username='edituser', password='pass')
        self.other_user = User.objects.create_user(username='editother', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('500.00'))
        self.future_date = date.today() + timedelta(days=30)
        self.schedule = RecurringTransaction.objects.create(
            user=self.user,
            mode='EXPENSE',
            amount=Decimal('40.00'),
            currency='GHS',
            account=self.account,
            frequency=RecurringFrequencyChoices.MONTHLY,
            renewal_date=date.today(),
            next_run_date=self.future_date,
            is_auto_renew=False,
        )
        self.client.force_login(self.user)

    def _post_data(self, **overrides):
        data = {
            'mode': self.schedule.mode,
            'amount': str(self.schedule.amount),
            'currency': self.schedule.currency,
            'account': str(self.account.pk),
            'category': '',
            'details': '',
            'reference': '',
            'tags_input': '',
            'frequency': self.schedule.frequency,
            'renewal_date': self.schedule.renewal_date.isoformat(),
            'end_date': '',
        }
        data.update(overrides)
        return data

    def test_editing_non_scheduling_field_keeps_next_run_date(self):
        url = reverse('spending_tracker:edit_recurring_transaction', args=[self.schedule.pk])
        response = self.client.post(url, self._post_data(amount='99.00', details='Updated'))
        self.assertRedirects(response, reverse('spending_tracker:recurring_list'))

        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.amount, Decimal('99.00'))
        self.assertEqual(self.schedule.details, 'Updated')
        self.assertEqual(self.schedule.next_run_date, self.future_date)

    def test_editing_frequency_reschedules_from_today(self):
        url = reverse('spending_tracker:edit_recurring_transaction', args=[self.schedule.pk])
        response = self.client.post(url, self._post_data(frequency='DAILY'))
        self.assertRedirects(response, reverse('spending_tracker:recurring_list'))

        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.frequency, 'DAILY')
        self.assertEqual(self.schedule.next_run_date, date.today())

    def test_editing_does_not_affect_already_created_transaction(self):
        auto_schedule = RecurringTransaction.objects.create(
            user=self.user, mode='EXPENSE', amount=Decimal('40.00'), currency='GHS',
            account=self.account, frequency=RecurringFrequencyChoices.DAILY,
            renewal_date=date.today(), is_auto_renew=True,
        )
        process_due_occurrences(auto_schedule, today=date.today())
        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=auto_schedule)
        self.assertEqual(occurrence.transaction.amount, Decimal('40.00'))

        url = reverse('spending_tracker:edit_recurring_transaction', args=[auto_schedule.pk])
        data = self._post_data(frequency='DAILY', amount='999.00')
        data['renewal_date'] = auto_schedule.renewal_date.isoformat()
        self.client.post(url, data)

        occurrence.refresh_from_db()
        self.assertEqual(occurrence.transaction.amount, Decimal('40.00'))

    def test_editing_updates_tags(self):
        url = reverse('spending_tracker:edit_recurring_transaction', args=[self.schedule.pk])
        self.client.post(url, self._post_data(tags_input='rent, monthly'))

        self.schedule.refresh_from_db()
        self.assertEqual(sorted(tag.label for tag in self.schedule.tags.all()), ['monthly', 'rent'])

    def test_other_users_schedule_404s(self):
        self.client.force_login(self.other_user)
        url = reverse('spending_tracker:edit_recurring_transaction', args=[self.schedule.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ConfirmRecurringOccurrenceTests(TestCase):
    """Tests for the approval-notification's click-through target."""

    def setUp(self):
        self.user = User.objects.create_user(username='approveuser', password='pass')
        self.other_user = User.objects.create_user(username='otheruser', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('300.00'))
        self.today = date(2026, 6, 1)
        self.schedule = RecurringTransaction.objects.create(
            user=self.user,
            mode='EXPENSE',
            amount=Decimal('40.00'),
            currency='GHS',
            account=self.account,
            frequency=RecurringFrequencyChoices.MONTHLY,
            renewal_date=self.today,
            is_auto_renew=False,
        )
        process_due_occurrences(self.schedule, today=self.today)
        self.occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=self.schedule)
        self.client.force_login(self.user)

    def test_approve_creates_transaction_and_updates_balance(self):
        url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        self.client.post(url, {'action': 'approve'})

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, RecurringOccurrenceStatusChoices.CONFIRMED)
        self.assertIsNotNone(self.occurrence.transaction)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('260.00'))

    def test_dismiss_creates_no_transaction(self):
        url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        self.client.post(url, {'action': 'dismiss'})

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, RecurringOccurrenceStatusChoices.DISMISSED)
        self.assertIsNone(self.occurrence.transaction)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('300.00'))

    def test_second_action_on_resolved_occurrence_is_noop(self):
        url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        self.client.post(url, {'action': 'approve'})
        self.account.refresh_from_db()
        balance_after_first = self.account.balance

        self.client.post(url, {'action': 'approve'})
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, balance_after_first)

    def test_other_users_occurrence_404s(self):
        self.client.force_login(self.other_user)
        url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

