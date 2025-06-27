from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as django_login
from django.utils.timezone import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import SplitGroup, GroupMember, Expense, ExpenseSplit  
from django.db.models import Count, Q
from .forms import CustomUserCreationForm, ExpenseForm  
from django.db.models import Sum 
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import F
from django.views.decorators.cache import never_cache




def home(request):
    return HttpResponse("Hello, Django!")

def first_page(request):
    return render(request, 'hello/first_page.html')

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            response = redirect('dashboard')
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
    else:
        form = AuthenticationForm()
    
    response = render(request, 'hello/login.html', {'form': form, 'date': datetime.now()})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            django_login(request, user)
            return redirect('first_page')
    else:
        form = CustomUserCreationForm()
    return render(request, 'hello/signup.html', {'form': form})

@never_cache
@login_required
def dashboard(request):
    
    total_owed = ExpenseSplit.objects.filter(
        user=request.user,
        is_settled=False
    ).aggregate(total=Sum('share'))['total'] or 0
    

    total_owed_to_user = ExpenseSplit.objects.filter(
        expense__paid_by=request.user,
        is_settled=False
    ).exclude(user=request.user).aggregate(total=Sum('share'))['total'] or 0
    
    return render(request, 'hello/dashboard.html', {
        'total_owed': total_owed,
        'total_owed_to_user': total_owed_to_user,
    })

@never_cache
@login_required
def create_group(request):
    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST.get('description', '')
        group = SplitGroup.objects.create(name=name, description=description, creator=request.user)
        GroupMember.objects.create(group=group, user=request.user)
        return redirect('add_members', group_id=group.id)
    return render(request, 'hello/create_group.html')

@never_cache
@login_required
def add_members(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)

    if request.method == 'POST':
        if 'finalize' in request.POST:
            return redirect('view_group', group_id=group.id)
        elif 'user_id' in request.POST:
            user_id = request.POST.get('user_id')
            if user_id and user_id.isdigit():
                user = get_object_or_404(User, id=int(user_id))
                GroupMember.objects.get_or_create(group=group, user=user)

    
    search_query = request.GET.get('search', '')
    users = User.objects.exclude(id=request.user.id)
    if search_query:
        users = users.filter(username__icontains=search_query)

    added_ids = GroupMember.objects.filter(group=group).values_list('user_id', flat=True)

    return render(request, 'hello/add_members.html', {
        'group': group,
        'users': users,
        'added_ids': added_ids,
    })

@never_cache
@login_required
def list_groups(request):
    group_ids = GroupMember.objects.filter(user=request.user).values_list('group_id', flat=True)
    user_groups = SplitGroup.objects.filter(id__in=group_ids, is_active=True).order_by('-created_at')
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        user_groups = user_groups.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query))
    
    # Add pagination - show 6 groups per page
    paginator = Paginator(user_groups, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'hello/list_groups.html', {
        'page_obj': page_obj,
        'message': "Your Groups",
        'user': request.user
    })




@never_cache
@login_required
def soft_delete_group(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)
    
    
    if group.creator != request.user:
        return HttpResponseForbidden("You don't have permission to delete this group.")
    
    if request.method == 'POST':
        
        pending_splits = ExpenseSplit.objects.filter(
            expense__group=group,
            is_settled=False
        ).exclude(user=F('expense__paid_by'))  
        
        if pending_splits.exists():
            messages.error(request, 
                         "Cannot delete group - there are pending payments! "
                         "Settle all payments first.")
            return redirect('view_group', group_id=group.id)
        
        
        group.is_active = False
        group.save()
        messages.success(request, f"Group '{group.name}' has been archived")
        return redirect('list_groups')
    
    return HttpResponseForbidden()

@never_cache
@login_required
def view_group(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)
    members = GroupMember.objects.filter(group=group).select_related('user')
    

    expenses = group.expense_set.all()
    
    
    current_category = request.GET.get('category', 'all')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    current_sort = request.GET.get('sort', 'date_desc')
    
    
    if current_category != 'all':
        expenses = expenses.filter(category=current_category)
    
    if min_price:
        try:
            expenses = expenses.filter(amount__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            expenses = expenses.filter(amount__lte=float(max_price))
        except ValueError:
            pass
    
    # Apply sorting
    if current_sort == 'date_asc':
        expenses = expenses.order_by('date')
    elif current_sort == 'date_desc':
        expenses = expenses.order_by('-date')
    elif current_sort == 'name_asc':
        expenses = expenses.order_by('name')
    elif current_sort == 'name_desc':
        expenses = expenses.order_by('-name')
    elif current_sort == 'amount_asc':
        expenses = expenses.order_by('amount')
    elif current_sort == 'amount_desc':
        expenses = expenses.order_by('-amount')
    
    return render(request, 'hello/group_detail.html', {
        'group': group,
        'members': members,
        'expenses': expenses,  # Pass the filtered/sorted queryset
        'category_choices': Expense.CATEGORY_CHOICES,
        'current_category': current_category,
        'min_price': min_price,
        'max_price': max_price,
        'current_sort': current_sort,
        'user': request.user
    })

@never_cache
@login_required
def add_expense(request, group_id):
    group = get_object_or_404(SplitGroup, id=group_id)
    
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        return HttpResponseForbidden("You're not a member of this group")
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, group=group)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.group = group
            expense.paid_by = request.user
            expense.save()
            
            # Get selected members
            involved_members = form.cleaned_data['involved_members']
            total_members = involved_members.count()
            share_amount = expense.amount / total_members if total_members > 0 else 0
            
            # Create splits only for involved members
            for member in involved_members:
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=member.user,
                    share=round(share_amount, 2),
                    is_settled=(member.user == request.user)
                )
            return redirect('view_group', group_id=group.id)
    else:
        form = ExpenseForm(group=group)
        # Pre-select all members by default
        form.fields['involved_members'].initial = GroupMember.objects.filter(group=group)
    
    return render(request, 'hello/add_expense.html', {'group': group, 'form': form})

@never_cache
@login_required
def mark_paid(request, split_id):
    split = get_object_or_404(ExpenseSplit, id=split_id)
    
    # Only the expense creator (payer) can mark splits as paid
    if request.method == 'POST' and split.expense.paid_by == request.user:
        split.is_settled = True
        split.save()
        messages.success(request, f"Marked {split.user.username}'s payment as complete!")
    else:
        messages.error(request, "Only the expense creator can confirm payments")
    
    return redirect('view_group', group_id=split.expense.group.id)

@never_cache
@login_required
def amounts_owed(request):
    # Calculate amounts user owes to others
    owed_splits = ExpenseSplit.objects.filter(
        user=request.user,
        is_settled=False
    ).select_related('expense', 'expense__group', 'expense__paid_by')
    
    total_owed = owed_splits.aggregate(total=Sum('share'))['total'] or 0
    
    return render(request, 'hello/amounts_owed.html', {
        'owed_splits': owed_splits,
        'total_owed': total_owed,
    })

@never_cache
@login_required
def amounts_to_receive(request):
    # Calculate amounts owed to user
    owed_to_user = ExpenseSplit.objects.filter(
        expense__paid_by=request.user,
        is_settled=False
    ).exclude(user=request.user).select_related('expense', 'expense__group', 'user')
    
    total_owed_to_user = owed_to_user.aggregate(total=Sum('share'))['total'] or 0
    
    return render(request, 'hello/amounts_to_receive.html', {
        'owed_to_user': owed_to_user,
        'total_owed_to_user': total_owed_to_user,
    })

@never_cache
@login_required
def remove_member(request, group_id, user_id):
    if request.method != 'POST':
        return HttpResponseForbidden()
        
    group = get_object_or_404(SplitGroup, id=group_id)
    user_to_remove = get_object_or_404(User, id=user_id)
    
    # Permission checks
    if group.creator != request.user:
        return HttpResponseForbidden("Only group creator can remove members")
    if user_to_remove == request.user:
        return HttpResponseForbidden("Cannot remove yourself as creator")

    # Check for pending payments
    pending_splits = ExpenseSplit.objects.filter(
        user=user_to_remove,
        expense__group=group,
        is_settled=False
    ).exclude(expense__paid_by=user_to_remove)  # Exclude splits they paid for
    
    if pending_splits.exists():
        messages.error(request, f"Cannot remove {user_to_remove.username} - they have pending payments!")
        return redirect('view_group', group_id=group.id)
    
    # If no pending payments, proceed with deletion
    GroupMember.objects.filter(group=group, user=user_to_remove).delete()
    messages.success(request, f"{user_to_remove.username} has been removed from the group")
    return redirect('view_group', group_id=group.id)