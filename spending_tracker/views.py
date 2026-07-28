import json
import logging
import uuid
from collections import OrderedDict
from datetime import timedelta, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Value, Prefetch
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.db.transaction import atomic
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from utils.paginator import apply_pagination
from .forms import (
    TransactionForm, AccountForm, CategoryForm, RecurringTransactionForm, ConfirmOccurrenceForm,
)
from .models import (
    Account, Transaction, Category, Tag, UserPreferences, CURRENCY_SYMBOLS, TransactionModeChoices,
    RecurringTransaction, RecurringTransactionOccurrence, RecurringOccurrenceStatusChoices,
)
from .services import process_due_occurrences

# Configure logger
logger = logging.getLogger(__name__)


def _get_currency_symbol(user):
    """Get currency symbol for the user's default currency."""
    preferences, _ = UserPreferences.objects.get_or_create(
        user=user, defaults={'default_currency': 'GHS'}
    )
    return CURRENCY_SYMBOLS.get(preferences.default_currency, preferences.default_currency)


def _group_transactions(transactions, group_by):
    """
    Group a list of Transaction objects by a time period.
    Returns list of dicts: {label, transactions, income_total, expense_total}.
    """
    groups = OrderedDict()

    for tx in transactions:
        dt = tx.transaction_time

        if group_by == 'day':
            key = dt.date()
            label = dt.strftime('%A, %-d %b %Y')
        elif group_by == 'week':
            monday = dt.date() - timedelta(days=dt.weekday())
            key = monday
            label = f'Week of {monday.strftime("%-d %b %Y")}'
        elif group_by == 'month':
            key = (dt.year, dt.month)
            label = dt.strftime('%B %Y')
        elif group_by == 'quarter':
            quarter = (dt.month - 1) // 3 + 1
            key = (dt.year, quarter)
            label = f'Q{quarter} {dt.year}'
        else:  # year
            key = dt.year
            label = str(dt.year)

        if key not in groups:
            groups[key] = {
                'label': label,
                'transactions': [],
                'income_total': Decimal('0.00'),
                'expense_total': Decimal('0.00'),
            }

        groups[key]['transactions'].append(tx)
        if tx.mode == 'INCOME':
            groups[key]['income_total'] += tx.amount
        elif tx.mode == 'EXPENSE':
            groups[key]['expense_total'] += tx.amount

    return list(groups.values())


def _is_partial(request):
    return request.GET.get('partial') == '1'


def _render_fragment(request, template_name, page_obj, extra_context=None):
    context = {'page_obj': page_obj}
    if extra_context:
        context.update(extra_context)
    html = render_to_string(template_name, context, request=request)
    response = HttpResponse(html)
    response['X-Has-Next'] = '1' if page_obj.has_next() else '0'
    return response


@login_required
def dashboard(request):
    """Main dashboard view"""
    user_accounts = Account.objects.filter(user=request.user)
    recent_transactions = Transaction.objects.filter(
        account__user=request.user
    ).select_related('account', 'category').prefetch_related('tags')[:10]

    # Calculate totals
    total_balance = user_accounts.aggregate(total=Sum('balance'))['total'] or 0

    # Monthly income/expense
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_income = Transaction.objects.filter(
        account__user=request.user,
        mode='INCOME',
        transaction_time__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly_expense = Transaction.objects.filter(
        account__user=request.user,
        mode='EXPENSE',
        transaction_time__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'accounts': user_accounts,
        'recent_transactions': recent_transactions,
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'net_monthly': monthly_income - monthly_expense,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/dashboard.html', context)


@login_required
def add_account(request):
    """Add a new account"""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created successfully!')
            return redirect('spending_tracker:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AccountForm()

    return render(request, 'spending_tracker/add_account.html', {'form': form})


@login_required
def transaction_list(request):
    """List all transactions for the user"""
    transactions = Transaction.objects.filter(
        account__user=request.user
    ).select_related('account', 'category').prefetch_related('tags')

    # Filter by mode
    mode_filter = request.GET.get('mode')
    if mode_filter in TransactionModeChoices.names_list():
        transactions = transactions.filter(mode=mode_filter)

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        transactions = transactions.filter(category_id=category_filter)

    # Filter by account
    account_filter = request.GET.get('account')
    if account_filter:
        transactions = transactions.filter(account_id=account_filter)

    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        transactions = transactions.filter(transaction_time__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_time__date__lte=date_to)

    # Sort
    allowed_sorts = {
        '-transaction_time': 'Newest First',
        'transaction_time': 'Oldest First',
        '-amount': 'Highest Amount',
        'amount': 'Lowest Amount',
    }
    sort_value = request.GET.get('sort', '-transaction_time')
    if sort_value not in allowed_sorts:
        sort_value = '-transaction_time'
    transactions = transactions.order_by(sort_value)

    # Grouping
    allowed_group_by = {'day', 'week', 'month', 'quarter', 'year'}
    group_by = request.GET.get('group_by', '').lower()
    if group_by not in allowed_group_by:
        group_by = ''

    if group_by:
        all_groups = _group_transactions(list(transactions), group_by)
        page_obj = apply_pagination(all_groups, request.GET.get('page'), 5)
        grouped_transactions = page_obj.object_list
    else:
        grouped_transactions = None
        page_obj = apply_pagination(transactions, request.GET.get('page'), 10)

    if _is_partial(request):
        if group_by:
            return _render_fragment(
                request,
                'spending_tracker/partials/_transactions_grouped_fragment.html',
                page_obj,
                {'currency_symbol': _get_currency_symbol(request.user)},
            )
        return _render_fragment(
            request,
            'spending_tracker/partials/_transactions_flat_fragment.html',
            page_obj,
        )

    # Build query string without page for pagination links
    query_params = {}
    if mode_filter:
        query_params['mode'] = mode_filter
    if category_filter:
        query_params['category'] = category_filter
    if account_filter:
        query_params['account'] = account_filter
    if sort_value != '-transaction_time':
        query_params['sort'] = sort_value
    if date_from:
        query_params['date_from'] = date_from
    if date_to:
        query_params['date_to'] = date_to
    if group_by:
        query_params['group_by'] = group_by

    context = {
        'page_obj': page_obj,
        'grouped_transactions': grouped_transactions,
        'group_by': group_by,
        'categories': Category.objects.filter(user=request.user),
        'accounts': Account.objects.filter(user=request.user),
        'currency_symbol': _get_currency_symbol(request.user),
        'current_sort': sort_value,
        'sort_options': allowed_sorts,
        'query_params': query_params,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'spending_tracker/transaction_list.html', context)


@login_required
def add_transaction(request):
    """Add new transaction - Multi-step: mode selection then form.

    The same form doubles as the "schedule a recurring transaction" form: checking
    "Make this a recurring transaction" reveals extra schedule fields, and submitting
    creates a RecurringTransaction (processed immediately if due) instead of a one-off
    Transaction.
    """
    # Get mode from query parameter
    mode = request.GET.get('mode', '').upper()

    # Check if there's preserved form data in session
    preserved_data = request.session.pop('transaction_form_data', None)
    preserved_tags = request.session.pop('transaction_tags_input', None)

    if preserved_data:
        logger.debug(
            f"Retrieved preserved transaction data from session: mode={request.session.get('transaction_mode')}, fields={list(preserved_data.keys())}")

    # Step 1: Show mode selection if no mode specified
    if not mode or mode not in TransactionModeChoices.names_list():
        logger.debug("No mode specified, showing mode selection page")
        return render(request, 'spending_tracker/add_transaction.html', {
            'show_mode_selection': True
        })

    is_recurring = request.method == 'POST' and request.POST.get('is_recurring') == 'true'
    recurring_form = None

    # Step 2: Show form for selected mode
    if request.method == 'POST':
        # Idempotency check
        submitted_token = request.POST.get('idempotency_token')
        session_token = request.session.pop('idempotency_token', None)
        if not submitted_token or submitted_token != session_token:
            messages.error(request, 'This transaction has already been submitted. Please try again.')
            return redirect(f"{reverse('spending_tracker:add_transaction')}?mode={mode}")

        # Get the tags input before form validation
        tags_input = request.POST.get('tags_input', '').strip()

        # Create a mutable copy of POST data
        post_data = request.POST.copy()
        # Remove tags from the form data as we'll handle them separately
        post_data.pop('tags', None)

        form = TransactionForm(post_data, request.FILES, user=request.user)

        if is_recurring:
            # The recurring schedule's renewal date is just the date part of the transaction's
            # own date/time — no need to make the user enter the same date twice.
            if post_data.get('transaction_time'):
                post_data['renewal_date'] = post_data['transaction_time'][:10]
            recurring_form = RecurringTransactionForm(post_data, user=request.user)
            # Validate the shared fields via `form` too, purely so the existing
            # form.<field>.errors blocks in the template still light up correctly.
            if form.is_valid() and recurring_form.is_valid():
                recurring_transaction = recurring_form.save(commit=False)
                recurring_transaction.user = request.user
                recurring_transaction.save()

                recurring_transaction.tags.add(*Tag.get_or_create_from_input(request.user, tags_input))

                # A schedule due today (or later) always processes immediately. One whose next
                # run is already in the past (a backdated renewal date) only catches up if the
                # user explicitly opted in via the "create and backdate" checkbox.
                today = timezone.localdate()
                if recurring_transaction.next_run_date >= today or request.POST.get('create_backdated') == 'true':
                    process_due_occurrences(recurring_transaction, today=today)

                messages.success(request, 'Recurring transaction scheduled successfully!')
                request.session.pop('transaction_form_data', None)
                request.session.pop('transaction_tags_input', None)
                request.session.pop('transaction_mode', None)
                return redirect('spending_tracker:recurring_list')
            else:
                messages.error(request, 'Please correct the errors below.')
                logger.warning(f"Recurring transaction validation failed: {form.errors} {recurring_form.errors}")
        elif form.is_valid():
            transaction = form.save()
            transaction.tags.add(*Tag.get_or_create_from_input(request.user, tags_input))

            messages.success(request, 'Transaction added successfully!')
            # Clear any preserved data
            request.session.pop('transaction_form_data', None)
            request.session.pop('transaction_tags_input', None)
            request.session.pop('transaction_mode', None)
            logger.debug("Transaction saved successfully, cleared preserved data from session")
            return redirect('spending_tracker:transaction_list')
        else:
            messages.error(request, 'Invalid data provided.')
            logger.warning(f"Transaction form validation failed: {form.errors}")
    else:
        # If there's preserved data from session, use it
        if preserved_data:
            logger.debug(f"Using preserved data to populate form with {len(preserved_data)} fields")
            form = TransactionForm(preserved_data, user=request.user)
        else:
            logger.debug("No preserved data, creating empty form")
            form = TransactionForm(user=request.user)

    if recurring_form is None:
        recurring_form = RecurringTransactionForm(user=request.user)

    is_recurring_checked = is_recurring if request.method == 'POST' else (preserved_data or {}).get('is_recurring') == 'true'

    default_account = Account.objects.filter(user=request.user).first()
    if not default_account:
        messages.warning(request, 'No accounts found. Please add an account first.')
        return redirect('spending_tracker:add_account')

    # Only set default account if no data is being preserved
    if not preserved_data and not form.is_bound:
        form.fields['account'].initial = default_account.id
        # Pre-set the mode
        form.fields['mode'].initial = mode

    all_currency = [i[0] for i in Transaction.CURRENCY_CHOICES]
    all_accounts = Account.objects.filter(user=request.user)
    user_category = Category.objects.filter(user=request.user)
    user_tags = list(Tag.objects.filter(user=request.user))

    # Generate idempotency token for the form
    idempotency_token = uuid.uuid4().hex
    request.session['idempotency_token'] = idempotency_token

    context = {
        'form': form,
        'recurring_form': recurring_form,
        'is_recurring_checked': is_recurring_checked,
        'mode': mode,
        'show_mode_selection': False,
        'default_account': default_account,
        'all_currency': all_currency,
        'all_accounts': all_accounts,
        'all_category': user_category,
        'tags': user_tags,
        'weekday_choices': RecurringTransactionForm.WEEKDAY_CHOICES,
        'preserved_tags_input': preserved_tags or '',
        'preserved_data': preserved_data or {},
        'currency_symbol': _get_currency_symbol(request.user),
        'idempotency_token': idempotency_token,
    }
    return render(request, 'spending_tracker/add_transaction.html', context)


@login_required
@require_http_methods(["POST"])
def delete_transaction(request, pk):
    """Delete a transaction (reverse its balance impact)"""
    transaction = get_object_or_404(Transaction, id=pk, account__user=request.user)
    transaction.delete()
    messages.success(request, 'Transaction reversed successfully!')
    return redirect('spending_tracker:transaction_list')


@login_required
def edit_transaction(request, pk):
    """Edit a transaction within 24-hour window"""
    transaction = get_object_or_404(
        Transaction.objects.select_related('account', 'category', 'recurring_occurrence__recurring_transaction')
        .prefetch_related('tags'),
        id=pk, account__user=request.user
    )

    if not transaction.is_editable:
        messages.error(request, 'This transaction can no longer be edited. The 24-hour edit window has passed.')
        return redirect('spending_tracker:transaction_list')

    if request.method == 'POST':
        tags_input = request.POST.get('tags_input', '').strip()
        post_data = request.POST.copy()
        post_data.pop('tags', None)

        form = TransactionForm(post_data, instance=transaction, user=request.user)
        if form.is_valid():
            with atomic():
                updated_transaction = form.save()

                updated_transaction.tags.set(Tag.get_or_create_from_input(request.user, tags_input))

            messages.success(request, 'Transaction updated successfully!')
            return redirect('spending_tracker:transaction_list')
        else:
            messages.error(request, 'Invalid data provided.')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    # Calculate remaining edit time
    edit_deadline = transaction.created_at + timedelta(hours=24)
    remaining = edit_deadline - timezone.now()
    remaining_hours = int(remaining.total_seconds() // 3600)
    remaining_minutes = int((remaining.total_seconds() % 3600) // 60)

    existing_tags = ', '.join(tag.label for tag in transaction.tags.all())
    recurring_occurrence = getattr(transaction, 'recurring_occurrence', None)

    context = {
        'form': form,
        'transaction': transaction,
        'recurring_occurrence': recurring_occurrence,
        'mode': transaction.mode,
        'remaining_hours': remaining_hours,
        'remaining_minutes': remaining_minutes,
        'existing_tags': existing_tags,
        'all_accounts': Account.objects.filter(user=request.user),
        'all_category': Category.objects.filter(user=request.user),
        'all_currency': [i[0] for i in Transaction.CURRENCY_CHOICES],
        'tags': list(Tag.objects.filter(user=request.user)),
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/edit_transaction.html', context)


@login_required
def add_tag(request):
    """Add new tag"""
    if request.method == 'POST':
        # Preserve transaction form data before processing
        transaction_data = {}
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'label'] and not key.startswith('tag_'):
                transaction_data[key] = value

        if transaction_data:
            request.session['transaction_form_data'] = transaction_data
            request.session['transaction_tags_input'] = request.POST.get('tags_input', '')

        tag = request.POST.get('label', '').strip().title()
        if tag:
            Tag.objects.create(label=tag, user=request.user)
            messages.success(request, 'Tag added successfully!')
        else:
            messages.error(request, 'Please enter a tag or label.')
    return redirect('spending_tracker:add_transaction')


@login_required
def add_category(request):
    """Add new category from transaction page"""
    if request.method == 'POST':
        # Preserve transaction form data before processing
        transaction_data = {}
        mode = request.POST.get('mode', 'EXPENSE')  # Get the mode from form

        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'label', 'description'] and not key.startswith('category_'):
                transaction_data[key] = value

        if transaction_data:
            request.session['transaction_form_data'] = transaction_data
            request.session['transaction_tags_input'] = request.POST.get('tags_input', '')
            request.session['transaction_mode'] = mode
            logger.debug(f"Preserved transaction data: mode={mode}, fields={list(transaction_data.keys())}")

        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f'Category "{category.label}" created successfully!')
            logger.debug(f"Category created: {category.label}")
        else:
            messages.error(request, 'Please correct the errors.')
            logger.warning(f"Category form errors: {form.errors}")

    # Redirect back to transaction form with mode parameter
    saved_mode = request.session.get('transaction_mode', 'EXPENSE')
    return redirect(f"{reverse('spending_tracker:add_transaction')}?mode={saved_mode}")


@login_required
def add_account_quick(request):
    """Add new account from transaction page"""
    if request.method == 'POST':
        # Preserve transaction form data before processing
        transaction_data = {}
        mode = request.POST.get('mode', 'EXPENSE')  # Get the mode from form

        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'name', 'balance', 'account_type'] and not key.startswith('account_'):
                transaction_data[key] = value

        if transaction_data:
            request.session['transaction_form_data'] = transaction_data
            request.session['transaction_tags_input'] = request.POST.get('tags_input', '')
            request.session['transaction_mode'] = mode
            logger.debug(f"Preserved transaction data: mode={mode}, fields={list(transaction_data.keys())}")

        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created successfully!')
            logger.debug(f"Account created: {account.name}")
        else:
            messages.error(request, 'Please correct the errors.')
            logger.warning(f"Account form errors: {form.errors}")

    # Redirect back to transaction form with mode parameter
    saved_mode = request.session.get('transaction_mode', 'EXPENSE')
    return redirect(f"{reverse('spending_tracker:add_transaction')}?mode={saved_mode}")


@login_required
def account_detail(request, pk):
    """View account details and transactions"""
    account = get_object_or_404(Account, id=pk, user=request.user)
    transactions = account.transactions.all().select_related('category').prefetch_related('tags')
    transactions_page = apply_pagination(transactions, request.GET.get('page'), 10)

    if _is_partial(request):
        return _render_fragment(
            request,
            'spending_tracker/partials/_account_detail_transactions_fragment.html',
            transactions_page,
        )

    context = {
        'account': account,
        'transactions': transactions,
        'transactions_page': transactions_page,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/account_detail.html', context)


@login_required
def accounts_list(request):
    """List all accounts with statistics"""
    accounts = Account.objects.filter(user=request.user).annotate(
        transaction_count=Count('transactions'),
        total_income=Sum('transactions__amount', filter=Q(transactions__mode='INCOME')),
        total_expenses=Sum('transactions__amount', filter=Q(transactions__mode='EXPENSE')),
        total_transfers_out=Sum('transactions__amount', filter=Q(transactions__mode='TRANSFER')),
        total_transfers_in=Sum('incoming_transfers__amount'),
    ).order_by('-balance')

    # Calculate total balance across all accounts
    total_balance = accounts.aggregate(total=Sum('balance'))['total'] or 0

    # Prepare account statistics
    account_stats = []
    for account in accounts:
        income = account.total_income or 0
        expenses = account.total_expenses or 0
        transfers_out = account.total_transfers_out or 0
        transfers_in = account.total_transfers_in or 0
        net_flow = income - expenses - transfers_out + transfers_in

        account_stats.append({
            'account': account,
            'transaction_count': account.transaction_count,
            'total_income': income,
            'total_expenses': expenses,
            'net_flow': net_flow,
        })

    context = {
        'accounts': accounts,
        'account_stats': account_stats,
        'total_balance': total_balance,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/accounts_list.html', context)


@login_required
def reports(request):
    """Financial reports and analytics"""
    period = request.GET.get('period', 'month')
    modifier = request.GET.get('modifier', 'this')  # this, last, last_three
    custom_start = request.GET.get('start_date')
    custom_end = request.GET.get('end_date')

    now = timezone.now()

    # Get user preferences for currency
    preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={'default_currency': 'GHS'}
    )

    user_currency = preferences.default_currency
    currency_symbol = CURRENCY_SYMBOLS.get(user_currency, user_currency)

    logger.debug(f"\n{'=' * 80}")
    logger.debug(f"=== REPORTS VIEW CALLED ===")
    logger.debug(f"{'=' * 80}")
    logger.debug(f"User: {request.user.username}")
    logger.debug(f"Currency: {user_currency} ({currency_symbol})")
    logger.debug(f"REQUEST PARAMS:")
    logger.debug(f"  - period: {period}")
    logger.debug(f"  - modifier: {modifier}")
    logger.debug(f"  - start_date: {custom_start}")
    logger.debug(f"  - end_date: {custom_end}")
    logger.debug(f"  - All GET params: {dict(request.GET)}")

    if custom_start and custom_end:
        try:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date.replace(hour=0, minute=0, second=0))
            end_date = datetime.strptime(custom_end, '%Y-%m-%d')
            end_date = timezone.make_aware(end_date.replace(hour=23, minute=59, second=59))
            period_name = f'{custom_start} to {custom_end}'
            period = 'custom'
        except ValueError:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Month'
            period = 'month'
            modifier = 'this'
    elif period == 'week':
        if modifier == 'this':
            # Current week (Monday to today)
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Week'
        elif modifier == 'last':
            # Last week (Monday to Sunday)
            last_monday = now - timedelta(days=now.weekday() + 7)
            start_date = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (last_monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            period_name = 'Last Week'
        elif modifier == 'last_three':
            # Last 3 weeks
            start_date = now - timedelta(days=21)
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'Last 3 Weeks'
        else:
            # Default to this week
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Week'
    elif period == 'year':
        if modifier == 'this':
            # Current year (Jan 1 to today)
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Year'
        elif modifier == 'last':
            # Last year (full year)
            last_year = now.year - 1
            start_date = now.replace(year=last_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(year=last_year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            period_name = f'{last_year}'
        elif modifier == 'last_three':
            # Last 3 years
            three_years_ago = now.year - 3
            start_date = now.replace(year=three_years_ago, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = f'Last 3 Years'
        else:
            # Default to this year
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Year'
    elif period == 'all_time':
        first_transaction = Transaction.objects.filter(account__user=request.user).order_by('transaction_time').first()
        start_date = first_transaction.transaction_time if first_transaction else now
        end_date = now
        period_name = 'All Time'
    else:  # month
        if modifier == 'this':
            # Current month (1st to today)
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Month'
        elif modifier == 'last':
            # Last month (full month)
            if now.month == 1:
                last_month_date = now.replace(year=now.year - 1, month=12, day=1)
            else:
                last_month_date = now.replace(month=now.month - 1, day=1)

            start_date = last_month_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Get last day of last month
            if last_month_date.month == 12:
                next_month = last_month_date.replace(year=last_month_date.year + 1, month=1, day=1)
            else:
                next_month = last_month_date.replace(month=last_month_date.month + 1, day=1)

            end_date = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            period_name = last_month_date.strftime('%B %Y')
        elif modifier == 'last_three':
            # Last 3 months
            if now.month <= 3:
                months_back = now.month - 1
                start_month = 12 - (2 - months_back)
                start_year = now.year - 1
            else:
                start_month = now.month - 3
                start_year = now.year

            start_date = now.replace(
                year=start_year, month=start_month, day=1,
                hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'Last 3 Months'
        else:
            # Default to this month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Month'

    logger.debug(f"\nDATE RANGE CALCULATED:")
    logger.debug(f"  - Period: {period}")
    logger.debug(f"  - Modifier: {modifier}")
    logger.debug(f"  - Period Name: {period_name}")
    logger.debug(f"  - Start: {start_date}")
    logger.debug(f"  - End: {end_date}")
    logger.debug(f"  - Days Difference: {(end_date - start_date).days}")

    base_transactions = Transaction.objects.filter(
        account__user=request.user,
        transaction_time__gte=start_date,
        transaction_time__lte=end_date
    ).select_related('account', 'category')

    # Apply optional account and category filters
    filter_account = request.GET.get('account')
    filter_category = request.GET.get('category')
    if filter_account:
        base_transactions = base_transactions.filter(account_id=filter_account)
    if filter_category:
        base_transactions = base_transactions.filter(category_id=filter_category)

    transaction_count = base_transactions.count()
    logger.debug(f"\nTRANSACTIONS FOUND:")
    logger.debug(f"  - Total transactions: {transaction_count}")

    if transaction_count > 0:
        sample_transaction = base_transactions.first()
        logger.debug(
            f"  - Sample transaction: {sample_transaction.mode} {sample_transaction.amount} on {sample_transaction.transaction_time}")
        income_count = base_transactions.filter(mode='INCOME').count()
        expense_count = base_transactions.filter(mode='EXPENSE').count()
        logger.debug(f"  - Income transactions: {income_count}")
        logger.debug(f"  - Expense transactions: {expense_count}")
    else:
        logger.warning(f"  - WARNING: No transactions found in this date range!")

    aggregated_data = base_transactions.aggregate(
        total_income=Sum('amount', filter=Q(mode='INCOME')),
        total_expenses=Sum('amount', filter=Q(mode='EXPENSE')),
        transaction_count=Count('id')
    )

    total_income = aggregated_data['total_income'] or 0
    total_expenses = aggregated_data['total_expenses'] or 0
    net_income = total_income - total_expenses

    logger.debug(f"\nAGGREGATED DATA:")
    logger.debug(f"  - Total Income: {currency_symbol}{total_income}")
    logger.debug(f"  - Total Expenses: {currency_symbol}{total_expenses}")
    logger.debug(f"  - Net Income: {currency_symbol}{net_income}")
    logger.debug(f"  - Transaction Count: {aggregated_data['transaction_count']}")

    savings_rate = (net_income / total_income * 100) if total_income > 0 else 0

    expense_categories = list(base_transactions.filter(mode='EXPENSE').values(
        category_label=Coalesce('category__label', Value('Uncategorized'))
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5])

    json_expense_categories = [
        {'label': record['category_label'], 'total': float(record['total']), 'count': record['count']}
        for record in expense_categories
    ]

    income_categories = base_transactions.filter(mode='INCOME').values(
        category_label=Coalesce('category__label', Value('Uncategorized'))
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]

    user_accounts = Account.objects.filter(user=request.user).prefetch_related(
        Prefetch(
            'transactions',
            queryset=base_transactions,
            to_attr='period_transactions'
        )
    )

    account_stats = base_transactions.values('account').annotate(
        income=Sum('amount', filter=Q(mode='INCOME')),
        expenses=Sum('amount', filter=Q(mode='EXPENSE')),
        transfers_out=Sum('amount', filter=Q(mode='TRANSFER')),
    )

    # Transfers received per account (destination side, not covered by account_stats)
    transfers_in_by_account = (
        base_transactions
        .filter(mode='TRANSFER', destination_account__isnull=False)
        .values('destination_account')
        .annotate(transfers_in=Sum('amount'))
    )
    transfers_in_dict = {row['destination_account']: row['transfers_in'] for row in transfers_in_by_account}

    account_stats_dict = {stat['account']: stat for stat in account_stats}

    account_performance = []
    for account in user_accounts:
        stats = account_stats_dict.get(account.id, {'income': 0, 'expenses': 0, 'transfers_out': 0})
        account_income = stats.get('income') or 0
        account_expenses = stats.get('expenses') or 0
        account_transfers_out = stats.get('transfers_out') or 0
        account_transfers_in = transfers_in_dict.get(account.id, 0) or 0
        net_change = account_income - account_expenses - account_transfers_out + account_transfers_in
        starting_balance = account.balance - net_change

        account_performance.append({
            'account': account,
            'starting_balance': round(starting_balance, 2),
            'income': round(account_income, 2),
            'expenses': round(account_expenses, 2),
            'net_change': round(net_change, 2),
            'current_balance': round(account.balance, 2),
        })

    days_diff = (end_date - start_date).days
    logger.debug(f"Days difference: {days_diff}")

    # Determine granularity based on period type
    if period == 'week':
        logger.debug("Processing WEEKLY trend data (daily granularity)")
        # Weekly filter: show each day of the week
        trend_results = base_transactions.annotate(
            period=TruncDate('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.debug(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup
        results_dict = {result['period']: result for result in trend_results}

        # Generate all days in the range up to current date
        trend_data = []
        current = start_date.date()
        end = min(end_date.date(), now.date())

        logger.debug(f"Generating daily data from {current} to {end}")

        while current <= end:
            result = results_dict.get(current, {})
            trend_data.append({
                'date': current.strftime('%a, %b %d'),
                'income': float(result.get('income') or 0),
                'expenses': float(result.get('expenses') or 0)
            })
            current += timedelta(days=1)

        logger.debug(f"Generated {len(trend_data)} daily data points")
        if trend_data:
            logger.debug(f"First data point: {trend_data[0]}")
            logger.debug(f"Last data point: {trend_data[-1]}")

    elif period == 'month':
        logger.debug("Processing MONTHLY trend data (weekly granularity)")
        # Monthly filter: show each week in the month
        trend_results = base_transactions.annotate(
            period=TruncWeek('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.debug(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup - convert datetime to date for consistent keys
        results_dict = {}
        for result in trend_results:
            # TruncWeek returns datetime, convert to date for key
            key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
            results_dict[key] = result
            logger.debug(f"  - Week {key}: Income={result.get('income', 0)}, Expenses={result.get('expenses', 0)}")

        # Generate all weeks in the month up to current date
        trend_data = []
        current = start_date
        end = min(end_date, now)

        # Get week start (Monday) for start_date
        current_week_start = current - timedelta(days=current.weekday())

        logger.debug(f"Generating weekly data from {current_week_start.date()} (week start)")

        while current_week_start <= end:
            # Only include if week start is within our period
            if current_week_start >= start_date or (current_week_start + timedelta(days=6)) >= start_date:
                week_date = current_week_start.date()
                result = results_dict.get(week_date, {})
                income_val = float(result.get('income') or 0)
                expense_val = float(result.get('expenses') or 0)

                # Only add week if it contains dates in our range and up to current date
                week_end = current_week_start + timedelta(days=6)
                if current_week_start <= end:
                    trend_data.append({
                        'date': week_date.strftime('%b %-d'),
                        'income': income_val,
                        'expenses': expense_val
                    })
                    logger.debug(
                        f"  - Week of {week_date}: Income={income_val}, Expenses={expense_val}, Found in results={week_date in results_dict}")

            current_week_start += timedelta(days=7)

        logger.debug(f"Generated {len(trend_data)} weekly data points")
        if trend_data:
            logger.debug(f"First data point: {trend_data[0]}")
            logger.debug(f"Last data point: {trend_data[-1]}")

    elif period == 'year':
        logger.debug("Processing YEARLY trend data (monthly granularity)")
        # Yearly filter: show each month in the year
        trend_results = base_transactions.annotate(
            period=TruncMonth('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.debug(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup - convert datetime to date for consistent keys
        results_dict = {}
        for result in trend_results:
            # TruncMonth returns datetime, convert to date for key
            key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
            results_dict[key] = result
            logger.debug(f"  - Month {key}: Income={result.get('income', 0)}, Expenses={result.get('expenses', 0)}")

        # Generate all months in the year up to the current month
        trend_data = []
        current = start_date.replace(day=1)
        end = min(end_date, now)

        logger.debug(f"Generating monthly data from {current.strftime('%b %Y')} to {end.strftime('%b %Y')}")

        while current <= end:
            month_date = current.date()
            result = results_dict.get(month_date, {})
            income_val = float(result.get('income') or 0)
            expense_val = float(result.get('expenses') or 0)

            trend_data.append({
                'date': current.strftime('%b %Y'),
                'income': income_val,
                'expenses': expense_val
            })

            logger.debug(
                f"  - {current.strftime('%b %Y')}: Income={income_val}, Expenses={expense_val}, Found in results={month_date in results_dict}")

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        logger.debug(f"Generated {len(trend_data)} monthly data points")
        if trend_data:
            logger.debug(f"First data point: {trend_data[0]}")
            logger.debug(f"Last data point: {trend_data[-1]}")

    else:
        logger.debug(f"Processing CUSTOM filter with {days_diff} days difference")
        # Custom filter: dynamic granularity based on range
        if days_diff < 35:  # Less than 5 weeks
            logger.debug("Custom: Using daily granularity (<35 days / 5 weeks)")
            # Less than 5 weeks: show by day
            trend_results = base_transactions.annotate(
                period=TruncDate('transaction_time')
            ).values('period').annotate(
                income=Sum('amount', filter=Q(mode='INCOME')),
                expenses=Sum('amount', filter=Q(mode='EXPENSE'))
            ).order_by('period')

            results_dict = {result['period']: result for result in trend_results}

            trend_data = []
            current = start_date.date()
            end = min(end_date.date(), now.date())

            while current <= end:
                result = results_dict.get(current, {})
                trend_data.append({
                    'date': current.strftime('%a, %b %d'),
                    'income': float(result.get('income') or 0),
                    'expenses': float(result.get('expenses') or 0)
                })
                current += timedelta(days=1)

        elif days_diff < 180:  # Less than 6 months
            logger.debug("Custom: Using weekly granularity (35-179 days / 5 weeks - 6 months)")
            # 35-179 days: show by week
            trend_results = base_transactions.annotate(
                period=TruncWeek('transaction_time')
            ).values('period').annotate(
                income=Sum('amount', filter=Q(mode='INCOME')),
                expenses=Sum('amount', filter=Q(mode='EXPENSE'))
            ).order_by('period')

            # Create dict for quick lookup - convert datetime to date for consistent keys
            results_dict = {}
            for result in trend_results:
                key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
                results_dict[key] = result

            trend_data = []
            current = start_date - timedelta(days=start_date.weekday())
            end = min(end_date, now)

            while current <= end:
                if current >= start_date or (current + timedelta(days=6)) >= start_date:
                    week_date = current.date()
                    result = results_dict.get(week_date, {})

                    if current <= end:
                        trend_data.append({
                            'date': week_date.strftime('%b %-d'),
                            'income': float(result.get('income') or 0),
                            'expenses': float(result.get('expenses') or 0)
                        })

                current += timedelta(days=7)

        elif days_diff <= 1095:  # Up to 3 years
            logger.debug("Custom: Using monthly granularity (180-1095 days / 6 months - 3 years)")
            # 180 days - 3 years: show by month
            trend_results = base_transactions.annotate(
                period=TruncMonth('transaction_time')
            ).values('period').annotate(
                income=Sum('amount', filter=Q(mode='INCOME')),
                expenses=Sum('amount', filter=Q(mode='EXPENSE'))
            ).order_by('period')

            # Create dict for quick lookup - convert datetime to date for consistent keys
            results_dict = {}
            for result in trend_results:
                key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
                results_dict[key] = result

            trend_data = []
            current = start_date.replace(day=1)
            end = min(end_date, now)

            while current <= end:
                month_date = current.date()
                result = results_dict.get(month_date, {})
                trend_data.append({
                    'date': current.strftime('%b %Y'),
                    'income': float(result.get('income') or 0),
                    'expenses': float(result.get('expenses') or 0)
                })

                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        else:
            logger.debug("Custom: Using yearly granularity (>1095 days / >3 years)")
            # More than 3 years: show by year
            from django.db.models.functions import ExtractYear

            trend_results = base_transactions.annotate(
                year=ExtractYear('transaction_time')
            ).values('year').annotate(
                income=Sum('amount', filter=Q(mode='INCOME')),
                expenses=Sum('amount', filter=Q(mode='EXPENSE'))
            ).order_by('year')

            results_dict = {result['year']: result for result in trend_results}

            trend_data = []
            current_year = start_date.year
            end_year = min(end_date.year, now.year)

            while current_year <= end_year:
                result = results_dict.get(current_year, {})
                trend_data.append({
                    'date': str(current_year),
                    'income': float(result.get('income') or 0),
                    'expenses': float(result.get('expenses') or 0)
                })
                current_year += 1

            logger.debug(f"Generated {len(trend_data)} yearly data points")

    logger.debug(f"\nFINAL CONTEXT DATA:")
    logger.debug(f"  - Trend data points: {len(trend_data)}")
    if trend_data and len(trend_data) > 0:
        logger.debug(f"    - First point: {trend_data[0]}")
        logger.debug(f"    - Last point: {trend_data[-1]}")
    logger.debug(f"  - Expense categories: {len(json_expense_categories)}")
    logger.debug(f"  - Income categories: {len(list(income_categories))}")
    logger.debug(f"  - Account performance rows: {len(account_performance)}")
    logger.debug(f"{'=' * 80}")
    logger.debug(f"=== REPORTS VIEW COMPLETE ===")
    logger.debug(f"{'=' * 80}\n")

    # Transfer analysis
    transfers = (
        base_transactions
        .filter(mode='TRANSFER')
        .select_related('account', 'destination_account', 'category')
        .order_by('-transaction_time')
    )
    transfer_agg = transfers.aggregate(
        total_volume=Sum('amount'),
        transfer_count=Count('id'),
    )
    total_transfer_volume = round(float(transfer_agg['total_volume'] or 0), 2)
    transfer_count = transfer_agg['transfer_count'] or 0

    # Most common source and destination accounts for transfers
    transfer_by_source = (
        transfers.values('account__name')
        .annotate(count=Count('id'), volume=Sum('amount'))
        .order_by('-volume')[:5]
    )
    transfer_by_dest = (
        transfers.filter(destination_account__isnull=False)
        .values('destination_account__name')
        .annotate(count=Count('id'), volume=Sum('amount'))
        .order_by('-volume')[:5]
    )

    # Compute summary metrics (Feature 9)
    days_in_period = max((end_date - start_date).days, 1)
    avg_daily_spending = round(float(total_expenses) / days_in_period, 2)

    top_expense_category = None
    top_expense_amount = 0
    if expense_categories:
        first_cat = list(expense_categories)[0]
        top_expense_category = first_cat['category_label']
        top_expense_amount = round(first_cat['total'], 2)

    income_expense_ratio = round(float(total_income) / float(total_expenses), 2) if total_expenses > 0 else 0

    context = {
        'period': period,
        'modifier': modifier,
        'period_name': period_name,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'net_income': round(net_income, 2),
        'savings_rate': round(savings_rate, 1),
        'expense_categories': expense_categories,
        'json_expense_categories': json_expense_categories,
        'income_categories': income_categories,
        'trend_data': trend_data,
        'account_performance': account_performance,
        'currency_symbol': currency_symbol,
        'user_currency': user_currency,
        # Report filters (Feature 8)
        'filter_accounts': Account.objects.filter(user=request.user),
        'filter_categories': Category.objects.filter(user=request.user),
        'selected_account': filter_account or '',
        'selected_category': filter_category or '',
        # Summary metrics (Feature 9)
        'avg_daily_spending': avg_daily_spending,
        'top_expense_category': top_expense_category,
        'top_expense_amount': top_expense_amount,
        'income_expense_ratio': income_expense_ratio,
        # Transfer analysis
        'transfers': transfers,
        'transfer_count': transfer_count,
        'total_transfer_volume': total_transfer_volume,
        'transfer_by_source': transfer_by_source,
        'transfer_by_dest': transfer_by_dest,
    }
    return render(request, 'spending_tracker/reports.html', context)


# Configuration and Management Views
@login_required
def config(request):
    """Configuration page for user preferences, accounts, and categories"""
    # Get or create user preferences
    preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={'default_currency': 'GHS'}
    )

    if request.method == 'POST':
        # Handle preference updates
        new_currency = request.POST.get('default_currency')
        if new_currency and new_currency in dict(Transaction.CURRENCY_CHOICES):
            preferences.default_currency = new_currency
            preferences.save()
            messages.success(request, 'Preferences updated successfully!')
            return redirect('spending_tracker:config')

    # Get user accounts with transaction counts
    accounts = Account.objects.filter(user=request.user).annotate(
        transaction_count=Count('transactions')
    ).order_by('name')

    # Get user categories with transaction counts
    categories = Category.objects.filter(user=request.user).annotate(
        transaction_count=Count('transactions')
    ).order_by('label')

    context = {
        'preferences': preferences,
        'accounts': accounts,
        'categories': categories,
        'currency_choices': Transaction.CURRENCY_CHOICES,
        'currency_symbol': CURRENCY_SYMBOLS.get(preferences.default_currency, preferences.default_currency),
    }
    return render(request, 'spending_tracker/config.html', context)


@login_required
def edit_account(request, pk):
    """Edit an existing account"""
    account = get_object_or_404(Account.objects.prefetch_related(
        'transactions'
    ).annotate(
        transaction_count=Count('transactions')
    ), id=pk, user=request.user)

    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account "{account.name}" updated successfully!')
            return redirect('spending_tracker:config')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AccountForm(instance=account)

    context = {
        'form': form,
        'account': account,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/edit_account.html', context)


@login_required
def delete_account(request, pk):
    """Delete an account with option to transfer transactions"""
    account = get_object_or_404(Account, id=pk, user=request.user)
    transaction_count = account.transactions.count()

    # Check if this is the only account
    user_accounts_count = Account.objects.filter(user=request.user).count()
    if user_accounts_count == 1:
        messages.error(request, 'Cannot delete your only account. Create another account first.')
        return redirect('spending_tracker:config')

    if request.method == 'POST':
        transfer_to_id = request.POST.get('transfer_to')

        if transaction_count > 0:
            if not transfer_to_id:
                messages.error(request, 'Please select an account to transfer transactions to.')
                return redirect('spending_tracker:delete_account', pk=pk)

            transfer_account = get_object_or_404(Account, id=transfer_to_id, user=request.user)

            if transfer_account.id == account.id:
                messages.error(request, 'Cannot transfer to the same account.')
                return redirect('spending_tracker:delete_account', pk=pk)

            # Transfer all transactions
            with atomic():
                account.transactions.update(account=transfer_account)
                account.delete()

            messages.success(request,
                             f'Account "{account.name}" deleted and {transaction_count} '
                             f'transaction(s) transferred to "{transfer_account.name}".')
        else:
            account.delete()
            messages.success(request, f'Account "{account.name}" deleted successfully!')

        return redirect('spending_tracker:config')

    # Get other accounts for transfer option
    other_accounts = Account.objects.filter(user=request.user).exclude(id=pk)

    context = {
        'account': account,
        'transaction_count': transaction_count,
        'other_accounts': other_accounts,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/delete_account.html', context)


@login_required
def edit_category(request, pk):
    """Edit an existing category"""
    category = get_object_or_404(Category.objects.prefetch_related(
        'transactions'
    ).annotate(
        transaction_count=Count('transactions')
    ), id=pk, user=request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.label}" updated successfully!')
            return redirect('spending_tracker:config')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
    }
    return render(request, 'spending_tracker/edit_category.html', context)


@login_required
def delete_category(request, pk):
    """Delete a category with option to transfer transactions"""
    category = get_object_or_404(Category, id=pk, user=request.user)
    transaction_count = category.transactions.count()

    if request.method == 'POST':
        transfer_to_id = request.POST.get('transfer_to')

        if transaction_count > 0:
            if not transfer_to_id:
                # Allow setting to None (Uncategorized)
                if request.POST.get('set_uncategorized') == 'yes':
                    with atomic():
                        category.transactions.update(category=None)
                        category.delete()
                    messages.success(request,
                                     f'Category "{category.label}" deleted and {transaction_count} '
                                     f'transaction(s) set to Uncategorized.')
                    return redirect('spending_tracker:config')
                else:
                    messages.error(request,
                                   'Please select a category to transfer transactions to or mark them as Uncategorized.')
                    return redirect('spending_tracker:delete_category', pk=pk)

            transfer_category = get_object_or_404(Category, id=transfer_to_id, user=request.user)

            if transfer_category.id == category.id:
                messages.error(request, 'Cannot transfer to the same category.')
                return redirect('spending_tracker:delete_category', pk=pk)

            # Transfer all transactions
            with atomic():
                category.transactions.update(category=transfer_category)
                category.delete()

            messages.success(request,
                             f'Category "{category.label}" deleted and {transaction_count} '
                             f'transaction(s) transferred to "{transfer_category.label}".')
        else:
            category.delete()
            messages.success(request, f'Category "{category.label}" deleted successfully!')

        return redirect('spending_tracker:config')

    # Get other categories for transfer option
    other_categories = Category.objects.filter(user=request.user).exclude(id=pk)

    context = {
        'category': category,
        'transaction_count': transaction_count,
        'other_categories': other_categories,
    }
    return render(request, 'spending_tracker/delete_category.html', context)


@login_required
@require_http_methods(["POST"])
def create_transaction_api(request):
    """API endpoint for creating transactions (used by background sync)"""
    try:
        data = json.loads(request.body)

        # Get user's default account or first account
        account = Account.objects.filter(user=request.user, is_default=True).first()
        if not account:
            account = Account.objects.filter(user=request.user).first()

        if not account:
            return JsonResponse({
                'error': 'No account found for user'
            }, status=400)

        # Get category if provided
        category = None
        category_id = data.get('category_id')
        if category_id:
            category = Category.objects.filter(id=category_id, user=request.user).first()

        # Get destination account for transfers
        destination_account = None
        destination_account_id = data.get('destination_account_id')
        if destination_account_id:
            destination_account = Account.objects.filter(id=destination_account_id, user=request.user).first()

        transaction = Transaction.objects.create(
            mode=data.get('mode', 'EXPENSE'),
            amount=Decimal(str(data.get('amount'))),
            currency=data.get('currency', 'GHS'),
            details=data.get('details', ''),
            account=account,
            destination_account=destination_account,
            category=category
        )

        # Send push notification to user
        try:
            from pwa.services import send_push_notification
            send_push_notification(
                user=request.user,
                title='Transaction Recorded',
                body=f'{transaction.mode}: {transaction.currency} {transaction.amount}',
                url='/spending_tracker/'
            )
        except Exception as e:
            logger.warning(f'Failed to send push notification: {e}')

        return JsonResponse({
            'success': True,
            'id': transaction.id
        })

    except Exception as e:
        logger.error(f'Failed to create transaction via API: {e}')
        return JsonResponse({
            'error': str(e)
        }, status=500)


# Recurring Transactions
@login_required
def edit_recurring_transaction(request, pk):
    """Edit a recurring transaction schedule, reusing the same field set as Add Transaction's
    recurring fields. Changes only affect future runs — already-created occurrences/transactions
    are untouched, and if scheduling rules change, next_run_date is recomputed from today rather
    than left at whatever the old rule had queued up."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    scheduling_fields = ['frequency', 'custom_type', 'custom_weekdays', 'custom_month_days']

    if request.method == 'POST':
        tags_input = request.POST.get('tags_input', '').strip()
        post_data = request.POST.copy()
        post_data.pop('tags', None)

        normalize = lambda value: value if value else None  # treat '', None, [] as equivalent
        before = {field: normalize(getattr(recurring_transaction, field)) for field in scheduling_fields}

        recurring_form = RecurringTransactionForm(post_data, instance=recurring_transaction, user=request.user)
        if recurring_form.is_valid():
            updated = recurring_form.save(commit=False)
            after = {field: normalize(getattr(updated, field)) for field in scheduling_fields}
            if after != before:
                updated.reschedule()
            updated.save()

            updated.tags.clear()
            if tags_input:
                tag_labels = [tag.strip().lower() for tag in tags_input.split(',') if tag.strip()]
                for tag_label in tag_labels:
                    tag, _ = Tag.objects.get_or_create(label=tag_label, defaults={'user': request.user})
                    updated.tags.add(tag)

            # If editing (e.g. changing the frequency) pushed next_run_date into the past,
            # only catch it up now if the user explicitly opted in via the checkbox.
            today = timezone.localdate()
            if updated.next_run_date < today and request.POST.get('create_backdated') == 'true':
                process_due_occurrences(updated, today=today)

            messages.success(request, 'Recurring transaction updated. Changes apply to future runs.')
            return redirect('spending_tracker:recurring_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            logger.warning(f"RecurringTransactionForm validation failed on edit: {recurring_form.errors}")
    else:
        recurring_form = RecurringTransactionForm(instance=recurring_transaction, user=request.user)

    context = {
        'recurring_form': recurring_form,
        'recurring_transaction': recurring_transaction,
        'tags': list(Tag.objects.filter(user=request.user)),
        'existing_tags': ', '.join(tag.label for tag in recurring_transaction.tags.all()),
        'currency_symbol': _get_currency_symbol(request.user),
        'today': timezone.localdate(),
    }
    return render(request, 'spending_tracker/edit_recurring_transaction.html', context)


@login_required
def recurring_list(request):
    """List the user's recurring transaction schedules and any pending approvals."""
    recurring_transactions = RecurringTransaction.objects.filter(user=request.user).select_related(
        'account', 'destination_account', 'category'
    )
    pending_occurrences = RecurringTransactionOccurrence.objects.filter(
        recurring_transaction__user=request.user,
        status=RecurringOccurrenceStatusChoices.PENDING,
    ).select_related('recurring_transaction')

    context = {
        'recurring_transactions': recurring_transactions,
        'pending_occurrences': pending_occurrences,
        'currency_symbol': _get_currency_symbol(request.user),
    }
    return render(request, 'spending_tracker/recurring_list.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_recurring_transaction(request, pk):
    """Pause or resume a recurring transaction schedule."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    recurring_transaction.is_active = not recurring_transaction.is_active
    recurring_transaction.save()
    state = 'resumed' if recurring_transaction.is_active else 'paused'
    messages.success(request, f'Recurring transaction {state}.')
    return redirect('spending_tracker:recurring_list')


@login_required
@require_http_methods(["POST"])
def delete_recurring_transaction(request, pk):
    """Delete a recurring transaction schedule. Transactions already created from it are unaffected."""
    recurring_transaction = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
    recurring_transaction.delete()
    messages.success(request, 'Recurring transaction deleted.')
    return redirect('spending_tracker:recurring_list')


@login_required
@require_http_methods(["POST"])
def clear_pending_occurrences(request):
    """Dismiss every pending approval the user has, in one go.

    This is the bulk form of the confirm view's 'dismiss' action, so it only ever skips —
    it never creates transactions. Bulk-approving is deliberately not offered: each approval
    moves money and is editable before it is committed, so it stays a per-occurrence decision.

    The update is filtered on PENDING rather than applied to a pre-read list, so a second
    submission (double tap, two tabs) can't rewrite `resolved_at` on already-resolved rows.
    """
    cleared = RecurringTransactionOccurrence.objects.filter(
        recurring_transaction__user=request.user,
        status=RecurringOccurrenceStatusChoices.PENDING,
    ).update(
        status=RecurringOccurrenceStatusChoices.DISMISSED,
        resolved_at=timezone.now(),
    )

    if cleared:
        messages.success(request, f"Cleared {cleared} pending approval{'' if cleared == 1 else 's'}.")
    else:
        messages.info(request, 'No pending approvals to clear.')
    return redirect('spending_tracker:recurring_list')


@login_required
def confirm_recurring_occurrence(request, pk):
    """Approve or dismiss a pending recurring transaction occurrence (the notification's CTA target).

    A push notification's link can outlive what it points to — e.g. the user deletes the
    recurring schedule (which cascades to its occurrences) before acting on an older
    notification. Rather than 404 on a stale link, send them back to the recurring list.
    """
    occurrence = RecurringTransactionOccurrence.objects.select_related(
        'recurring_transaction', 'recurring_transaction__account'
    ).filter(pk=pk).first()

    if occurrence is None:
        messages.info(request, 'This recurring transaction no longer exists.')
        return redirect('spending_tracker:recurring_list')

    # Belongs to someone else: a real 404, not a "gone" redirect — don't leak that the pk exists.
    if occurrence.recurring_transaction.user_id != request.user.id:
        raise Http404

    # Stale notification link (already acted on, e.g. from a re-delivered push or a second tab).
    # Send the user to where the outcome actually lives instead of re-showing a dead approval form.
    if occurrence.status != RecurringOccurrenceStatusChoices.PENDING:
        if occurrence.transaction_id:
            messages.info(request, 'This recurring transaction was already confirmed.')
            return redirect(f"{reverse('spending_tracker:transaction_list')}?highlight={occurrence.transaction_id}")
        messages.info(request, 'This recurring transaction occurrence was already dismissed.')
        return redirect('spending_tracker:recurring_list')

    recurring_transaction = occurrence.recurring_transaction
    form = None

    if request.method == 'POST':
        action = request.POST.get('action')

        # Skipping resolves the occurrence outright; there is nothing to validate.
        if action == 'dismiss':
            occurrence.status = RecurringOccurrenceStatusChoices.DISMISSED
            occurrence.resolved_at = timezone.now()
            occurrence.save()
            messages.success(request, 'Skipped this one.')
            return redirect('spending_tracker:recurring_list')

        form = ConfirmOccurrenceForm(
            request.POST,
            request.FILES,
            user=request.user,
            recurring_transaction=recurring_transaction,
            scheduled_date=occurrence.scheduled_date,
        )
        if form.is_valid():
            tags = Tag.get_or_create_from_input(request.user, form.cleaned_data['tags_input'])
            with atomic():
                # A fresh instance, so Transaction.save() takes its create branch and applies
                # the balance impact exactly once. mode/currency/reference are already on it.
                created_transaction = form.save(commit=False)
                created_transaction.save()
                created_transaction.tags.set(tags)

                occurrence.status = RecurringOccurrenceStatusChoices.CONFIRMED
                occurrence.transaction = created_transaction
                occurrence.resolved_at = timezone.now()
                occurrence.save()
            try:
                from pwa.services import send_push_notification
                send_push_notification(
                    user=request.user,
                    title='Transaction Created',
                    body=f'{created_transaction.get_mode_display()}: {created_transaction.currency} {created_transaction.amount}',
                    url=f'/spending_tracker/transactions/?highlight={created_transaction.pk}',
                )
            except Exception as e:
                logger.warning(f'Failed to send push notification: {e}')
            messages.success(request, 'Confirmed.')
            return redirect('spending_tracker:recurring_list')
        # Invalid: fall through and re-render the bound form. The occurrence stays PENDING.

    if form is None:
        form = ConfirmOccurrenceForm(
            user=request.user,
            recurring_transaction=recurring_transaction,
            scheduled_date=occurrence.scheduled_date,
        )

    context = {
        'occurrence': occurrence,
        'recurring_transaction': recurring_transaction,
        'form': form,
        'currency_symbol': recurring_transaction.currency_symbol,
    }
    return render(request, 'spending_tracker/confirm_recurring_occurrence.html', context)
