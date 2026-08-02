from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Account, Category, Tag, Transaction, RecurringTransaction, RecurringTransactionOccurrence,
    RecurringFrequencyChoices, CustomRecurrenceTypeChoices, RecurringOccurrenceStatusChoices,
)
from .services import process_due_occurrences
from .templatetags.spending_extras import humanize_amount


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
        self.assertEqual(occurrence.transaction.transaction_time.date(), self.today)

        schedule.refresh_from_db()
        self.assertEqual(schedule.next_run_date, self.today + timedelta(days=1))

    def test_backdated_catchup_transactions_use_their_own_scheduled_dates(self):
        # Renewal date is 2 days in the past, so this single run catches up on 3 occurrences
        # (today-2, today-1, today) — each should be dated to when it was due, not to "now".
        schedule = self._schedule(is_auto_renew=True, renewal_date=self.today - timedelta(days=2))
        process_due_occurrences(schedule, today=self.today)

        occurrences = RecurringTransactionOccurrence.objects.filter(recurring_transaction=schedule).order_by('scheduled_date')
        self.assertEqual(occurrences.count(), 3)
        for occurrence in occurrences:
            self.assertEqual(occurrence.transaction.transaction_time.date(), occurrence.scheduled_date)

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

    def test_auto_renew_notification_links_to_created_transaction(self):
        from domains.pwa.models import Notification

        schedule = self._schedule(is_auto_renew=True)
        process_due_occurrences(schedule, today=self.today)

        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=schedule, scheduled_date=self.today)
        notification = Notification.objects.get(user=self.user, title='Recurring Transaction Created')
        self.assertEqual(notification.url, f'/spending_tracker/transactions/?highlight={occurrence.transaction_id}')


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
        self.url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        self.client.force_login(self.user)

    def _approve_data(self, **overrides):
        """A valid approve payload. The confirm form is a real ModelForm, so amount,
        account and transaction_time all have to be present."""
        data = {
            'action': 'approve',
            'amount': '40.00',
            'account': self.account.pk,
            'transaction_time': '2026-06-01T09:00',
            'category': '',
            'details': '',
            'tags_input': '',
        }
        data.update(overrides)
        return data

    def test_approve_creates_transaction_and_updates_balance(self):
        self.client.post(self.url, self._approve_data())

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, RecurringOccurrenceStatusChoices.CONFIRMED)
        self.assertIsNotNone(self.occurrence.transaction)
        self.assertEqual(self.occurrence.transaction.transaction_time.date(), self.today)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('260.00'))

    def test_transaction_time_defaults_to_the_scheduled_date(self):
        response = self.client.get(self.url)
        initial = response.context['form'].fields['transaction_time'].initial
        self.assertTrue(initial.startswith('2026-06-01'), initial)

    def test_approve_with_edited_amount_creates_transaction_with_that_amount(self):
        self.client.post(self.url, self._approve_data(amount='63.00'))

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.transaction.amount, Decimal('63.00'))

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('237.00'))

    def test_approve_with_edited_amount_leaves_schedule_untouched(self):
        self.client.post(self.url, self._approve_data(amount='63.00'))

        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.amount, Decimal('40.00'))

    def test_approve_with_edited_account_uses_selected_account(self):
        other_account = Account.objects.create(name='Cash', user=self.user, balance=Decimal('100.00'))
        self.client.post(self.url, self._approve_data(account=other_account.pk))

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.transaction.account, other_account)

        other_account.refresh_from_db()
        self.account.refresh_from_db()
        self.assertEqual(other_account.balance, Decimal('60.00'))
        self.assertEqual(self.account.balance, Decimal('300.00'))

    def test_approve_applies_edited_details_and_tags(self):
        self.client.post(self.url, self._approve_data(details='Lunch at the canteen', tags_input='food, Daily'))

        self.occurrence.refresh_from_db()
        transaction = self.occurrence.transaction
        self.assertEqual(transaction.details, 'Lunch at the canteen')
        self.assertCountEqual([tag.label for tag in transaction.tags.all()], ['food', 'daily'])

    def test_approve_with_invalid_amount_rerenders_without_resolving(self):
        response = self.client.post(self.url, self._approve_data(amount='0'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, RecurringOccurrenceStatusChoices.PENDING)
        self.assertIsNone(self.occurrence.transaction)
        self.assertEqual(Transaction.objects.count(), 0)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('300.00'))

    def test_approve_transfer_rejects_destination_equal_to_source(self):
        """`mode` is not a field on the confirm form, so this only passes because the form
        stamps it onto the instance for TransactionForm.clean() to find."""
        destination = Account.objects.create(name='Savings', user=self.user, balance=Decimal('0.00'))
        transfer = RecurringTransaction.objects.create(
            user=self.user,
            mode='TRANSFER',
            amount=Decimal('40.00'),
            currency='GHS',
            account=self.account,
            destination_account=destination,
            frequency=RecurringFrequencyChoices.MONTHLY,
            renewal_date=self.today,
            is_auto_renew=False,
        )
        process_due_occurrences(transfer, today=self.today)
        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=transfer)
        url = reverse('spending_tracker:confirm_recurring_occurrence', args=[occurrence.pk])

        response = self.client.post(url, self._approve_data(destination_account=self.account.pk))

        self.assertEqual(response.status_code, 200)
        self.assertIn('destination_account', response.context['form'].errors)

        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, RecurringOccurrenceStatusChoices.PENDING)

    def test_dismiss_creates_no_transaction(self):
        self.client.post(self.url, {'action': 'dismiss'})

        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, RecurringOccurrenceStatusChoices.DISMISSED)
        self.assertIsNone(self.occurrence.transaction)

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('300.00'))

    def test_approve_notification_links_to_created_transaction(self):
        from domains.pwa.models import Notification

        self.client.post(self.url, self._approve_data())

        self.occurrence.refresh_from_db()
        notification = Notification.objects.get(user=self.user, title='Transaction Created')
        self.assertEqual(notification.url, f'/spending_tracker/transactions/?highlight={self.occurrence.transaction_id}')

    def test_second_action_on_resolved_occurrence_is_noop(self):
        self.client.post(self.url, self._approve_data())
        self.account.refresh_from_db()
        balance_after_first = self.account.balance

        self.client.post(self.url, self._approve_data())
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, balance_after_first)

    def test_stale_confirmed_link_redirects_to_highlighted_transaction(self):
        self.client.post(self.url, self._approve_data())
        self.occurrence.refresh_from_db()

        response = self.client.get(self.url)
        self.assertRedirects(
            response,
            f"{reverse('spending_tracker:transaction_list')}?highlight={self.occurrence.transaction_id}",
        )

    def test_stale_dismissed_link_redirects_to_recurring_list(self):
        self.client.post(self.url, {'action': 'dismiss'})

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('spending_tracker:recurring_list'))

    def test_other_users_occurrence_404s(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class RecurringListPendingRowTests(TestCase):
    """The pending-approval rows carry a review link over the whole card plus a
    skip action twice over — once behind the card for the touch swipe, once as an
    in-row button for pointer devices. CSS picks which is live."""

    def setUp(self):
        self.user = User.objects.create_user(username='pendingrowuser', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('300.00'))
        self.schedule = RecurringTransaction.objects.create(
            user=self.user, mode='EXPENSE', amount=Decimal('40.00'), currency='GHS',
            account=self.account, frequency=RecurringFrequencyChoices.MONTHLY,
            renewal_date=date(2026, 6, 1), is_auto_renew=False,
        )
        process_due_occurrences(self.schedule, today=date(2026, 6, 1))
        self.occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=self.schedule)
        self.url = reverse('spending_tracker:recurring_list')
        self.client.force_login(self.user)

    def test_row_is_a_link_to_the_confirm_page(self):
        confirm_url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{confirm_url}"')
        self.assertContains(response, 'class="pending-link"')

    def test_row_offers_a_dismiss_form_in_both_modes(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="action" value="dismiss"', count=2)
        self.assertContains(response, 'swipe-btn')   # behind the card, for the swipe
        self.assertContains(response, 'row-skip-btn')  # in the row, for pointer devices

    def test_no_separate_review_button(self):
        """Three references to the confirm URL per row — the card link plus the two
        skip forms. A fourth would mean the old Review button is back."""
        confirm_url = reverse('spending_tracker:confirm_recurring_occurrence', args=[self.occurrence.pk])
        response = self.client.get(self.url)
        self.assertContains(response, confirm_url, count=3)

    def test_resolved_occurrence_drops_out_of_the_pending_list(self):
        self.occurrence.status = RecurringOccurrenceStatusChoices.DISMISSED
        self.occurrence.save()

        response = self.client.get(self.url)
        self.assertNotContains(response, f'data-occurrence-id="{self.occurrence.pk}"')

    def test_schedule_row_carries_swipe_actions_and_a_tap_target(self):
        """The schedule cards below use the same shell: toggle + delete behind the
        card for touch, the full button set in-row for pointer devices."""
        edit_url = reverse('spending_tracker:edit_recurring_transaction', args=[self.schedule.pk])
        response = self.client.get(self.url)

        self.assertContains(response, f'data-recurring-id="{self.schedule.pk}"')
        self.assertContains(response, 'card-tap-target')
        self.assertContains(response, reverse('spending_tracker:toggle_recurring_transaction', args=[self.schedule.pk]), count=2)
        self.assertContains(response, reverse('spending_tracker:delete_recurring_transaction', args=[self.schedule.pk]), count=2)
        self.assertContains(response, edit_url, count=2)

    def test_schedule_row_has_no_full_swipe_commit(self):
        """Two actions and a destructive one: reveal-then-tap only, never a
        gesture that deletes on release."""
        response = self.client.get(self.url)
        self.assertContains(response, 'data-swipe-commit="true"', count=1)  # the pending row only


class EditTransactionRecurringBannerTests(TestCase):
    """Editing a one-off transaction should link back to its schedule when it was
    generated by a recurring occurrence, and say nothing otherwise."""

    def setUp(self):
        self.user = User.objects.create_user(username='editbanneruser', password='pass')
        self.account = Account.objects.create(name='Main', user=self.user, balance=Decimal('500.00'))
        self.client.force_login(self.user)

    def test_no_banner_for_plain_transaction(self):
        transaction = Transaction.objects.create(
            mode='EXPENSE', amount=Decimal('20.00'), currency='GHS',
            account=self.account, transaction_time=timezone.now(),
        )
        response = self.client.get(reverse('spending_tracker:edit_transaction', args=[transaction.pk]))
        self.assertNotContains(response, 'Created from a recurring schedule')

    def test_banner_links_to_schedule_for_transaction_from_occurrence(self):
        schedule = RecurringTransaction.objects.create(
            user=self.user, mode='EXPENSE', amount=Decimal('40.00'), currency='GHS',
            account=self.account, frequency=RecurringFrequencyChoices.MONTHLY,
            renewal_date=date.today(), is_auto_renew=True,
        )
        process_due_occurrences(schedule, today=date.today())
        occurrence = RecurringTransactionOccurrence.objects.get(recurring_transaction=schedule)

        response = self.client.get(reverse('spending_tracker:edit_transaction', args=[occurrence.transaction_id]))
        self.assertContains(response, 'Created from a recurring schedule')
        self.assertContains(
            response, reverse('spending_tracker:edit_recurring_transaction', args=[schedule.pk])
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
