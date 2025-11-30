from datetime import timedelta, datetime
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models as django_models
from django.db.models import Sum, Count, Q, Value, CharField, Prefetch
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.db.transaction import atomic
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from utils.paginator import apply_pagination
from .forms import TransactionForm, AccountForm, CategoryForm
from .models import Account, Transaction, Category, Tag, UserPreferences

# Configure logger
logger = logging.getLogger(__name__)


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
    if mode_filter in ['INCOME', 'EXPENSE']:
        transactions = transactions.filter(mode=mode_filter)

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        transactions = transactions.filter(category_id=category_filter)

    # Filter by account
    account_filter = request.GET.get('account')
    if account_filter:
        transactions = transactions.filter(account_id=account_filter)

    transaction_page = apply_pagination(transactions, request.GET.get('page'), 10)

    context = {
        'page_obj': transaction_page,
        'categories': Category.objects.all(),
        'accounts': Account.objects.filter(user=request.user),
    }
    return render(request, 'spending_tracker/transaction_list.html', context)


@login_required
def add_transaction(request):
    """Add new transaction"""
    # Check if there's preserved form data in session
    preserved_data = request.session.pop('transaction_form_data', None)
    preserved_tags = request.session.pop('transaction_tags_input', None)

    if request.method == 'POST':
        # Get the tags input before form validation
        tags_input = request.POST.get('tags_input', '').strip()

        # Create a mutable copy of POST data
        post_data = request.POST.copy()
        # Remove tags from the form data as we'll handle them separately
        post_data.pop('tags', None)

        form = TransactionForm(post_data, user=request.user)

        if form.is_valid():
            transaction = form.save()

            # Handle comma-separated tags
            if tags_input:
                tag_labels = [tag.strip().lower() for tag in tags_input.split(',') if tag.strip()]
                for tag_label in tag_labels:
                    tag, created = Tag.objects.get_or_create(
                        label=tag_label,
                        defaults={'user': request.user}
                    )
                    transaction.tags.add(tag)

            messages.success(request, 'Transaction added successfully!')
            # Clear any preserved data
            request.session.pop('transaction_form_data', None)
            request.session.pop('transaction_tags_input', None)
            return redirect('spending_tracker:transaction_list')
        else:
            messages.error(request, 'Invalid data provided.')
    else:
        # If there's preserved data from session, use it
        if preserved_data:
            form = TransactionForm(preserved_data, user=request.user)
        else:
            form = TransactionForm(user=request.user)

    default_account = Account.objects.filter(user=request.user).first()
    if not default_account:
        messages.warning(request, 'No accounts found. Please add an account first.')
        return redirect('spending_tracker:add_account')

    # Only set default account if no data is being preserved
    if not preserved_data and not form.is_bound:
        form.fields['account'].initial = default_account.id

    all_currency = [i[0] for i in Transaction.CURRENCY_CHOICES]
    all_accounts = Account.objects.filter(user=request.user)
    user_category = Category.objects.filter(user=request.user)
    user_tags = list(Tag.objects.filter(user=request.user))
    context = {
        'form': form,
        'default_account': default_account,
        'all_currency': all_currency,
        'all_accounts': all_accounts,
        'all_category': user_category,
        'tags': user_tags,
        'preserved_tags_input': preserved_tags or ''
    }
    return render(request, 'spending_tracker/add_transaction.html', context)


@login_required
def delete_transaction(request, pk):
    """Delete a transaction"""
    if request.method == 'GET':
        transaction = get_object_or_404(Transaction, id=pk, account__user=request.user)
        transaction.delete()
        messages.success(request, 'Transaction deleted!')

    return redirect('spending_tracker:transaction_list')


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
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'label', 'description'] and not key.startswith('category_'):
                transaction_data[key] = value

        if transaction_data:
            request.session['transaction_form_data'] = transaction_data
            request.session['transaction_tags_input'] = request.POST.get('tags_input', '')

        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f'Category "{category.label}" created successfully!')
        else:
            messages.error(request, 'Please correct the errors.')
    return redirect('spending_tracker:add_transaction')


@login_required
def add_account_quick(request):
    """Add new account from transaction page"""
    if request.method == 'POST':
        # Preserve transaction form data before processing
        transaction_data = {}
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'name', 'balance', 'account_type'] and not key.startswith('account_'):
                transaction_data[key] = value

        if transaction_data:
            request.session['transaction_form_data'] = transaction_data
            request.session['transaction_tags_input'] = request.POST.get('tags_input', '')

        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f'Account "{account.name}" created successfully!')
        else:
            messages.error(request, 'Please correct the errors.')
    return redirect('spending_tracker:add_transaction')


@login_required
def account_detail(request, pk):
    """View account details and transactions"""
    account = get_object_or_404(Account, id=pk, user=request.user)
    transactions = account.transactions.all().select_related('category').prefetch_related('tags')

    context = {
        'account': account,
        'transactions': transactions,
    }
    return render(request, 'spending_tracker/account_detail.html', context)


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

    # Currency symbol mapping
    CURRENCY_SYMBOLS = {
        'GHS': '₵',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
    }

    user_currency = preferences.default_currency
    currency_symbol = CURRENCY_SYMBOLS.get(user_currency, user_currency)

    logger.info(f"\n{'='*80}")
    logger.info(f"=== REPORTS VIEW CALLED ===")
    logger.info(f"{'='*80}")
    logger.info(f"User: {request.user.username}")
    logger.info(f"Currency: {user_currency} ({currency_symbol})")
    logger.info(f"REQUEST PARAMS:")
    logger.info(f"  - period: {period}")
    logger.info(f"  - modifier: {modifier}")
    logger.info(f"  - start_date: {custom_start}")
    logger.info(f"  - end_date: {custom_end}")
    logger.info(f"  - All GET params: {dict(request.GET)}")

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

            start_date = now.replace(year=start_year, month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'Last 3 Months'
        else:
            # Default to this month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = 'This Month'

    logger.info(f"\nDATE RANGE CALCULATED:")
    logger.info(f"  - Period: {period}")
    logger.info(f"  - Modifier: {modifier}")
    logger.info(f"  - Period Name: {period_name}")
    logger.info(f"  - Start: {start_date}")
    logger.info(f"  - End: {end_date}")
    logger.info(f"  - Days Difference: {(end_date - start_date).days}")

    base_transactions = Transaction.objects.filter(
        account__user=request.user,
        transaction_time__gte=start_date,
        transaction_time__lte=end_date
    ).select_related('account', 'category')

    transaction_count = base_transactions.count()
    logger.info(f"\nTRANSACTIONS FOUND:")
    logger.info(f"  - Total transactions: {transaction_count}")

    if transaction_count > 0:
        sample_transaction = base_transactions.first()
        logger.info(f"  - Sample transaction: {sample_transaction.mode} {sample_transaction.amount} on {sample_transaction.transaction_time}")
        income_count = base_transactions.filter(mode='INCOME').count()
        expense_count = base_transactions.filter(mode='EXPENSE').count()
        logger.info(f"  - Income transactions: {income_count}")
        logger.info(f"  - Expense transactions: {expense_count}")
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

    logger.info(f"\nAGGREGATED DATA:")
    logger.info(f"  - Total Income: {currency_symbol}{total_income}")
    logger.info(f"  - Total Expenses: {currency_symbol}{total_expenses}")
    logger.info(f"  - Net Income: {currency_symbol}{net_income}")
    logger.info(f"  - Transaction Count: {aggregated_data['transaction_count']}")

    savings_rate = (net_income / total_income * 100) if total_income > 0 else 0

    expense_categories = base_transactions.filter(mode='EXPENSE').values(
        category_label=Coalesce('category__label', Value('Uncategorized'))
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    json_expense_categories = [
        {'label': record['category_label'], 'total': float(record['total']), 'count': record['count']}
        for record in expense_categories
    ]

    income_categories = base_transactions.filter(mode='INCOME').values(
        category_label=Coalesce('category__label', Value('Uncategorized'))
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    user_accounts = Account.objects.filter(user=request.user).prefetch_related(
        Prefetch(
            'transactions',
            queryset=base_transactions,
            to_attr='period_transactions'
        )
    )

    account_stats = base_transactions.values('account').annotate(
        income=Sum('amount', filter=Q(mode='INCOME')),
        expenses=Sum('amount', filter=Q(mode='EXPENSE'))
    )

    account_stats_dict = {stat['account']: stat for stat in account_stats}

    account_performance = []
    for account in user_accounts:
        stats = account_stats_dict.get(account.id, {'income': 0, 'expenses': 0})
        account_income = stats.get('income') or 0
        account_expenses = stats.get('expenses') or 0
        net_change = account_income - account_expenses
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
    logger.info(f"Days difference: {days_diff}")

    # Determine granularity based on period type
    if period == 'week':
        logger.info("Processing WEEKLY trend data (daily granularity)")
        # Weekly filter: show each day of the week
        trend_results = base_transactions.annotate(
            period=TruncDate('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.info(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup
        results_dict = {result['period']: result for result in trend_results}

        # Generate all days in the range up to current date
        trend_data = []
        current = start_date.date()
        end = min(end_date.date(), now.date())

        logger.info(f"Generating daily data from {current} to {end}")

        while current <= end:
            result = results_dict.get(current, {})
            trend_data.append({
                'date': current.strftime('%a, %b %d'),
                'income': float(result.get('income') or 0),
                'expenses': float(result.get('expenses') or 0)
            })
            current += timedelta(days=1)

        logger.info(f"Generated {len(trend_data)} daily data points")
        if trend_data:
            logger.info(f"First data point: {trend_data[0]}")
            logger.info(f"Last data point: {trend_data[-1]}")

    elif period == 'month':
        logger.info("Processing MONTHLY trend data (weekly granularity)")
        # Monthly filter: show each week in the month
        trend_results = base_transactions.annotate(
            period=TruncWeek('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.info(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup - convert datetime to date for consistent keys
        results_dict = {}
        for result in trend_results:
            # TruncWeek returns datetime, convert to date for key
            key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
            results_dict[key] = result
            logger.info(f"  - Week {key}: Income={result.get('income', 0)}, Expenses={result.get('expenses', 0)}")

        # Generate all weeks in the month up to current date
        trend_data = []
        current = start_date
        end = min(end_date, now)
        week_num = 1

        # Get week start (Monday) for start_date
        from django.db.models.functions import TruncWeek as TruncWeekFunc
        current_week_start = current - timedelta(days=current.weekday())

        logger.info(f"Generating weekly data from {current_week_start.date()} (week start)")

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
                        'date': f"Week {week_num}",
                        'income': income_val,
                        'expenses': expense_val
                    })
                    logger.info(f"  - Week {week_num}: Income={income_val}, Expenses={expense_val}, Found in results={week_date in results_dict}")
                    week_num += 1

            current_week_start += timedelta(days=7)

        logger.info(f"Generated {len(trend_data)} weekly data points")
        if trend_data:
            logger.info(f"First data point: {trend_data[0]}")
            logger.info(f"Last data point: {trend_data[-1]}")

    elif period == 'year':
        logger.info("Processing YEARLY trend data (monthly granularity)")
        # Yearly filter: show each month in the year
        trend_results = base_transactions.annotate(
            period=TruncMonth('transaction_time')
        ).values('period').annotate(
            income=Sum('amount', filter=Q(mode='INCOME')),
            expenses=Sum('amount', filter=Q(mode='EXPENSE'))
        ).order_by('period')

        logger.info(f"Raw trend results count: {len(list(trend_results))}")

        # Create dict for quick lookup - convert datetime to date for consistent keys
        results_dict = {}
        for result in trend_results:
            # TruncMonth returns datetime, convert to date for key
            key = result['period'].date() if hasattr(result['period'], 'date') else result['period']
            results_dict[key] = result
            logger.info(f"  - Month {key}: Income={result.get('income', 0)}, Expenses={result.get('expenses', 0)}")

        # Generate all months in the year up to current month
        trend_data = []
        current = start_date.replace(day=1)
        end = min(end_date, now)

        logger.info(f"Generating monthly data from {current.strftime('%b %Y')} to {end.strftime('%b %Y')}")

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

            logger.info(f"  - {current.strftime('%b %Y')}: Income={income_val}, Expenses={expense_val}, Found in results={month_date in results_dict}")

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        logger.info(f"Generated {len(trend_data)} monthly data points")
        if trend_data:
            logger.info(f"First data point: {trend_data[0]}")
            logger.info(f"Last data point: {trend_data[-1]}")

    else:
        logger.info(f"Processing CUSTOM filter with {days_diff} days difference")
        # Custom filter: dynamic granularity based on range
        if days_diff < 35:  # Less than 5 weeks
            logger.info("Custom: Using daily granularity (<35 days / 5 weeks)")
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
            logger.info("Custom: Using weekly granularity (35-179 days / 5 weeks - 6 months)")
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
            week_num = 1

            while current <= end:
                if current >= start_date or (current + timedelta(days=6)) >= start_date:
                    week_date = current.date()
                    result = results_dict.get(week_date, {})

                    if current <= end:
                        trend_data.append({
                            'date': f"Week {week_num}",
                            'income': float(result.get('income') or 0),
                            'expenses': float(result.get('expenses') or 0)
                        })
                        week_num += 1

                current += timedelta(days=7)

        elif days_diff <= 1095:  # Up to 3 years
            logger.info("Custom: Using monthly granularity (180-1095 days / 6 months - 3 years)")
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
            logger.info("Custom: Using yearly granularity (>1095 days / >3 years)")
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

            logger.info(f"Generated {len(trend_data)} yearly data points")

    logger.info(f"\nFINAL CONTEXT DATA:")
    logger.info(f"  - Trend data points: {len(trend_data)}")
    if trend_data and len(trend_data) > 0:
        logger.info(f"    - First point: {trend_data[0]}")
        logger.info(f"    - Last point: {trend_data[-1]}")
    logger.info(f"  - Expense categories: {len(json_expense_categories)}")
    logger.info(f"  - Income categories: {len(list(income_categories))}")
    logger.info(f"  - Account performance rows: {len(account_performance)}")
    logger.info(f"{'='*80}")
    logger.info(f"=== REPORTS VIEW COMPLETE ===")
    logger.info(f"{'='*80}\n")

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
            with transaction.atomic():
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
                    messages.error(request, 'Please select a category to transfer transactions to or mark them as Uncategorized.')
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
