from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from utils.paginator import apply_pagination
from .forms import TransactionForm, AccountForm
from .models import Account, Transaction, Category, Tag


@login_required
def dashboard(request):
    """Main dashboard view"""
    user_accounts = Account.objects.filter(user=request.user)
    recent_transactions = Transaction.objects.filter(
        account__user=request.user
    ).select_related('account', 'category').prefetch_related('tags')[:10]

    # Calculate totals
    total_balance = user_accounts.aggregate(
        total=Sum('balance')
    )['total'] or 0

    # Monthly income/expense
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_income = Transaction.objects.filter(
        account__user=request.user,
        mode='INCOME',
        created_at__gte=current_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly_expense = Transaction.objects.filter(
        account__user=request.user,
        mode='EXPENSE',
        created_at__gte=current_month
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
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)

        if form.is_valid():
            transaction = form.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('spending_tracker:transaction_list')
        else:
            print(form.errors)
            messages.error(request, 'Kindly review the form.')
    else:
        form = TransactionForm(user=request.user)

    default_account = Account.objects.filter(user=request.user).first()
    if not default_account:
        messages.warning(request, 'No accounts found. Please add an account first.')
        return redirect('spending_tracker:add_account')

    form.fields['account'].initial = default_account.id
    all_currency = [i[0] for i in Transaction.CURRENCY_CHOICES]
    all_accounts = Account.objects.filter(user=request.user)
    user_category = Category.objects.all()
    user_tags = list(Tag.objects.filter(user=request.user))
    context = {
        'form': form,
        'default_account': default_account,
        'all_currency': all_currency,
        'all_accounts': all_accounts,
        'all_category': user_category,
        'tags': user_tags
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
        tag = request.POST.get('label', '').strip().title()
        if tag:
            Tag.objects.create(label=tag, user=request.user)
            messages.success(request, 'Tag added successfully!')
        else:
            messages.error(request, 'Please enter a tag or label.')
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
    # Get period parameter
    period = request.GET.get('period', 'month')

    # Calculate date ranges
    now = timezone.now()
    if period == 'week':
        start_date = now - timedelta(days=7)
        period_name = 'This Week'
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_name = 'This Year'
    else:  # default to month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_name = 'This Month'

    # Get user's transactions for the period
    transactions = Transaction.objects.filter(
        account__user=request.user,
        created_at__gte=start_date
    ).select_related('account', 'category')

    # Calculate key metrics
    total_income = transactions.filter(mode='INCOME').aggregate(
        total=Sum('amount'))['total'] or 0
    total_expenses = transactions.filter(mode='EXPENSE').aggregate(
        total=Sum('amount'))['total'] or 0
    net_income = total_income - total_expenses

    # Calculate savings rate
    savings_rate = 0
    if total_income > 0:
        savings_rate = (net_income / total_income) * 100

    # Category breakdown for expenses
    expense_categories = transactions.filter(mode='EXPENSE').values(
        'category__label'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    json_expense_categories = [dict(
        label=record.get('category__label'),
        total=record.get('total'),
        count=record.get('count'),
    ) for record in expense_categories]

    # Income sources breakdown
    income_categories = transactions.filter(mode='INCOME').values(
        'category__label'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]

    # Account performance
    user_accounts = Account.objects.filter(user=request.user)
    account_performance = []

    for account in user_accounts:
        account_transactions = transactions.filter(account=account)
        account_income = account_transactions.filter(mode='INCOME').aggregate(
            total=Sum('amount'))['total'] or 0
        account_expenses = account_transactions.filter(mode='EXPENSE').aggregate(
            total=Sum('amount'))['total'] or 0

        # Calculate starting balance (current balance - net transactions)
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

    # Daily/Weekly trend data for charts
    trend_data = []
    if period == 'week':
        # Daily data for the week
        for i in range(7):
            date = start_date + timedelta(days=i)
            day_transactions = transactions.filter(
                created_at__date=date.date()
            )
            daily_income = day_transactions.filter(mode='INCOME').aggregate(
                total=Sum('amount'))['total'] or 0
            daily_expenses = day_transactions.filter(mode='EXPENSE').aggregate(
                total=Sum('amount'))['total'] or 0

            trend_data.append({
                'date': date.strftime('%a, %b %d'),
                'income': float(daily_income),
                'expenses': float(daily_expenses),
            })
    else:
        # Weekly data for month/year
        current_date = start_date
        week_num = 1

        while current_date <= now:
            week_end = min(current_date + timedelta(days=6), now)
            week_transactions = transactions.filter(
                created_at__range=[current_date, week_end]
            )
            weekly_income = week_transactions.filter(mode='INCOME').aggregate(
                total=Sum('amount'))['total'] or 0
            weekly_expenses = week_transactions.filter(mode='EXPENSE').aggregate(
                total=Sum('amount'))['total'] or 0

            trend_data.append({
                'date': f'Week {week_num}',
                'income': float(weekly_income),
                'expenses': float(weekly_expenses),
            })

            current_date += timedelta(days=7)
            week_num += 1

            if len(trend_data) >= 12:  # Limit to prevent too much data
                break

    # Monthly comparison (for context)
    # current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # last_month = (current_month - timedelta(days=1)).replace(day=1)

    # current_month_income = Transaction.objects.filter(
    #     account__user=request.user,
    #     mode='INCOME',
    #     created_at__gte=current_month
    # ).aggregate(total=Sum('amount'))['total'] or 0

    # last_month_income = Transaction.objects.filter(
    #     account__user=request.user,
    #     mode='INCOME',
    #     created_at__gte=last_month,
    #     created_at__lt=current_month
    # ).aggregate(total=Sum('amount'))['total'] or 0

    # current_month_expenses = Transaction.objects.filter(
    #     account__user=request.user,
    #     mode='EXPENSE',
    #     created_at__gte=current_month
    # ).aggregate(total=Sum('amount'))['total'] or 0

    # last_month_expenses = Transaction.objects.filter(
    #     account__user=request.user,
    #     mode='EXPENSE',
    #     created_at__gte=last_month,
    #     created_at__lt=current_month
    # ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate month-over-month changes
    # income_change = (
    #             (current_month_income - last_month_income) / last_month_income * 100) if last_month_income > 0 else 0
    # expense_change = ((
    #                               current_month_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses > 0 else 0


    context = {
        'period': period,
        'period_name': period_name,
        'start_date': start_date,
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'net_income': round(net_income, 2),
        'savings_rate': round(savings_rate, 1),
        'expense_categories': expense_categories,
        'json_expense_categories': json_expense_categories,
        'income_categories': income_categories,
        'trend_data': trend_data,
        'account_performance': account_performance,
        # 'current_month_income': current_month_income,
        # 'last_month_income': last_month_income,
        # 'current_month_expenses': current_month_expenses,
        # 'last_month_expenses': last_month_expenses,
        # 'income_change': round(income_change, 1),
        # 'expense_change': round(expense_change, 1),
        # 'transaction_count': transactions.count(),
    }
    return render(request, 'spending_tracker/reports.html', context)
