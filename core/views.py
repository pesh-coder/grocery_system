from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, JsonResponse
from .models import *
from .forms import *
from datetime import date
import csv
from datetime import timedelta
from django.contrib import messages
from django.db.models import Sum, F, Min
from datetime import date
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
import json
# Create your views here.

TRUST_THRESHOLD = 3 

#This is the path for dashboard page
@login_required
 

def admin(request):
    sales = Sale.objects.all()
    today = date.today()

    # Monthly sales count
    sales_this_month = sales.filter(
        sale_date__year=today.year,
        sale_date__month=today.month
    ).count()

    total_sales = sum(
        [sale.total_amount for sale in sales if sale.amount_received >= sale.total_amount],
        Decimal('0.00')
    )

    User = get_user_model()
    total_stock = Inventory.objects.aggregate(total=Sum('quantity'))['total'] or 0

    # Top branch logic
    top_branch = (
        Branch.objects
        .annotate(
            sale__total_amount=Sum(
                'sale__total_amount',
                filter=Q(sale__sale_date__year=today.year, sale__sale_date__month=today.month)
            )
        )
        .order_by('-sale__total_amount')
        .first()
    )

    procurements = Procurement.objects.select_related('produce', 'branch', 'dealer').all()
    purchases_this_month = procurements.filter(
        actual_delivery_date__year=today.year,
        actual_delivery_date__month=today.month
    ).aggregate(total=Sum('total_cost'))['total'] or 0

    top_product = (
        procurements.filter(
            actual_delivery_date__year=today.year,
            actual_delivery_date__month=today.month
        )
        .values('produce__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')
        .first()
    )

    top_dealer = (
        procurements.filter(
            actual_delivery_date__year=today.year,
            actual_delivery_date__month=today.month
        )
        .values('dealer__name')
        .annotate(total_supplied=Sum('quantity'))
        .order_by('-total_supplied')
        .first()
    )

    # Credit: Total Due (sum where amount_received < total)
    total_credit_due = Sale.objects.filter(
        is_paid=False
    ).aggregate(total_due=Sum(F('total_amount') - F('amount_received')))['total_due'] or 0

    # Trusted Buyers: group by customer_name with 3+ successful transactions
    trusted_buyers = (
        Sale.objects.filter(is_paid=True)
        .values('customer_name')
        .annotate(count=Count('id'))
        .filter(count__gte=TRUST_THRESHOLD)
        .count()
    )

    # Upcoming Due Dates: within next 7 days
    upcoming_due_dates = Sale.objects.filter(
        is_paid=False,
        due_date__range=[today, today + timedelta(days=7)]
    )

    # Staff Counts
    total_managers = User.objects.filter(user_type='manager').count()
    total_sales_agents = User.objects.filter(user_type='sales_agent').count()

    # On-Duty Today (users who logged in today — assumes you track login)
    on_duty_staff = User.objects.filter(last_login__date=today).values_list('first_name', flat=True)

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'sales_this_month': sales_this_month,
        'total_transactions': sales.count(),
        'total_branches': Branch.objects.count(),
        'total_users': User.objects.count(),
        'total_inventory': Inventory.objects.count(),
        'total_stock': total_stock,
        'top_branch': top_branch,
        'purchases_this_month': purchases_this_month,
        'top_product': top_product,
        'top_dealer': top_dealer,
        'total_credit_due': total_credit_due,
        'trusted_buyers': trusted_buyers,
        'upcoming_due_dates': upcoming_due_dates,
        'total_managers': total_managers,
        'total_sales_agents': total_sales_agents,
        'on_duty_staff': list(on_duty_staff),
    }

    return render(request, 'core/dashboard3.html', context)


# health check
def health_check(request):
    return JsonResponse({"status": "ok", "message": "Healthy"})

@login_required
def branch(request):
    
    today = date.today()
    User = get_user_model()

    user = request.user
    if user.user_type == 'admin':
        total_companies = Procurement.objects.count()
        total_users = User.objects.count()
    else:
        total_companies = Procurement.objects.filter(branch=user.branch).count()
        total_users = User.objects.filter(branch=user.branch).count()

    total_products = Produce.objects.filter(dealer__branch=user.branch).count()
    sales_this_month_qs = Sale.objects.filter(sale_date__year=today.year,
        sale_date__month=today.month)

    payments_this_month = sum([sale.total_amount for sale in sales_this_month_qs if sale.amount_received >= sale.total_amount], Decimal('0.00'))


    sales_this_month = Sale.objects.filter(
        sale_date__year=today.year,
        sale_date__month=today.month
    ).count()

    # Top Selling Product
# Top Selling Product with fallback
top_product_data = Sale.objects.filter(
    sale_date__month=today.month
).values('produce__id', 'produce__name', 'produce__selling_price').annotate(
    total_quantity=Sum('quantity')
).order_by('-total_quantity').first()

# Fallback to all-time if no sales this month
if not top_product_data:
    top_product_data = Sale.objects.values('produce__id', 'produce__name', 'produce__selling_price').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity').first()

# Fetch the actual Produce object
top_product = None
if top_product_data:
    try:
        top_product = Produce.objects.get(id=top_product_data['produce__id'])
    except Produce.DoesNotExist:
        top_product = None

    # Latest Sales
    latest_sales = Sale.objects.order_by('-sale_date')[:5]

    # This will get the most recently active sales agent (based on last_login) in the same branch as the currently logged-in user.
    user = request.user
    on_duty_user = CustomUser.objects.filter(
        branch=user.branch,
        user_type='sales_agent'
    ).order_by('-last_login').first()

    user = request.user

    context = {
        'total_companies': total_companies,
        'total_users': total_users,
        'total_products': total_products,
        'payments_this_month': payments_this_month,
        'sales_this_month': sales_this_month,
        'top_product': top_product,
        'latest_sales': latest_sales,
        'on_duty_user': on_duty_user,
        'user_type': user.user_type,
        }

    return render(request, 'core/dashboard2.html', context)

@login_required
def global_search(request):
    query = request.GET.get('q', '')
    users = products = suppliers = []

    if query:
        users = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

        products = Produce.objects.filter(
            Q(name__icontains=query) |
            Q(type__icontains=query)
        )

        suppliers = Procurement.objects.filter(
            Q(dealer__name__icontains=query) 
        )

    # 🔁 Redirect if only one result exists
    if users.count() == 1 and products.count() == 0 and suppliers.count() == 0:
        return redirect('viewuser', pk=users.first().id)
    elif products.count() == 1 and users.count() == 0 and suppliers.count() == 0:
        return redirect('product_detail', pk=products.first().id)
    elif suppliers.count() == 1 and users.count() == 0 and products.count() == 0:
        return redirect('view_procurement', pk=suppliers.first().id)    

    context = {
        'query': query,
        'users': users,
        'products': products,
        'suppliers': suppliers
    }

    return render(request, 'core/search_results.html', context)

def Logout(request):
    return render(request, 'core/logout.html')

def Login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.user_type == 'admin':
                    return redirect('/dashboard3/')
                elif user.user_type in ['manager', 'sales_agent']:
                    return redirect('/dashboard2/') # Shared Dashboard
                else:
                    return redirect('/login/')  # fallback
        else:
            return render(request, 'core/index.html', {'form': form, 'error': 'Invalid credentials'})
    else:
        form = AuthenticationForm()
    return render(request, 'core/index.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserCreation(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            return redirect('/')
    else:
        form = UserCreation()
    return render(request, 'core/signup.html', {'form': form, 'title':'Sign Up'})

@login_required
def userspage(request):
    user = request.user
    if user.user_type == 'admin':
        users = CustomUser.objects.all()
    else:
        users = CustomUser.objects.filter(branch=user.branch)
    
    return render(request, 'core/users.html', {'users': users})

@login_required
def deleteuser(request, pk):
    user = request.user
    if user.user_type == 'admin':
        user = CustomUser.objects.get(pk=pk)
    else:
        user = CustomUser.objects.get(pk=pk, branch=user.branch)
    return render(request, 'core/deleteuser.html', {'user':user})

@login_required
def viewuser(request, pk):
    user = request.user
    if user.user_type == 'admin':
        user = CustomUser.objects.get(pk=pk)
    else:
        user = CustomUser.objects.get(pk=pk, branch=user.branch)
    return render(request, 'core/user_details.html', {'user': user})

@login_required
def edituser(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = CustomUserEditForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        messages.success(request, "User updated successfully!")
        return redirect('/users/')
    return render(request, 'core/edituser.html', {'form':form, 'user': user})


# products page
@login_required
def products_list(request):

    products = Produce.objects.all()

    
    product_filter = request.GET.get('product')
    if product_filter and product_filter != "all":
        products = products.filter(name=product_filter)

    product_names = products.values_list('name', flat=True).distinct()

    products = products.order_by('id')
    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    user = request.user
    can_edit = True  # Default

    if user.user_type == 'sales_agent':
        can_edit = False  # Sales Agent cannot edit or delete
    
    return render(request, 'core/products.html', {'products': products, 'product_names': product_names, 'selected_product': product_filter, 'can_edit': can_edit})

#product details.
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Produce, pk=pk)
    today = date.today()
    # Top Selling Product
    #Filters sales for the current month.
    top_product_data = Sale.objects.filter(
        sale_date__month=today.month
    #Groups results by produce__name and produce__selling_price    
    ).values('produce__id','produce__name', 'produce__selling_price').annotate(
        #Annotates each group with total_quantity.
        total_quantity=Sum('quantity')
    #Orders by highest quantity.
    ).order_by('-total_quantity').first() #Returns the top one. #with - DESCENDING from top to bottom
    '''
    This means that the one with the highest number of kgs bought in a month will be listed first
    '''

    is_top_seller = False
    if top_product_data:
        # Check if the current product is the top-selling one
        is_top_seller = (product.id == top_product_data['produce__id'])

    return render(request, 'core/product_detail.html', {'product': product, 'is_top_seller':is_top_seller })

#edit your products
@login_required
def edit_product(request, pk):
    user = request.user
    if user.user_type == 'admin':
        product = Produce.objects.get(pk=pk)
    else:
        product = Produce.objects.get(pk=pk, dealer__branch=user.branch) 

    if request.method == 'POST':
        form = ProduceForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('/products/')
    else:
        form = ProduceForm(instance=product)
    return render(request, 'core/edit_product.html', {'form': form, 'product': product})

#delete your products
@login_required
def delete_product(request, pk):
    user = request.user
    if user.user_type == 'admin':
        product = Produce.objects.get(pk=pk)
    else:
        product = Produce.objects.get(pk=pk, dealer__branch=user.branch) 
    product.delete()
    return redirect('/products/')

#add your products
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProduceForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f"{Produce.name} added successfully! Buying Price: UGX {Produce.buying_price}, Selling Price: UGX {Produce.selling_price}"
            )
            return redirect('/products/')  # After adding product, go back to product list
    else:
        form = ProduceForm(user=request.user)
    return render(request, 'core/add_product.html', {'form': form})


#This is the path for the inventory status page
@login_required
def inventory_status(request):
    user = request.user
    if user.user_type == 'admin':
       inventory = Inventory.objects.select_related('produce', 'branch').all()
    else:
        inventory = Inventory.objects.select_related('produce', 'branch').filter(branch=user.branch)
    
    query = request.GET.get('search')
    check_inventory = inventory.all()

    if query:
        check_inventory = check_inventory.filter(
            Q(produce__name__icontains=query) |
            Q(branch__name__icontains=query) |
            Q(quantity__icontains=query)
        )

    return render(request, 'core/inventory-status.html', {'inventory': inventory, 'check_inventory': check_inventory})


#This is the path for the procurement page

@login_required
def procurement_list(request):
    query = request.GET.get('search')
    user = request.user
    if user.user_type == 'admin':
        procurements = Procurement.objects.select_related('produce', 'branch', 'dealer').all()
    else:
        procurements = Procurement.objects.select_related('produce', 'branch', 'dealer').filter(branch=user.branch) 

    if query:
        procurements = procurements.filter(
            Q(produce__name__icontains=query) |
            Q(branch__name__icontains=query) |
            Q(dealer__name__icontains=query) |
            Q(quantity__icontains=query)
        )

    supplier_filter = request.GET.get('supplier')

    if supplier_filter and supplier_filter != "all":
        procurements = procurements.filter(dealer__name=supplier_filter)

    dealer_names = procurements.values_list('dealer__name', flat=True).distinct()

    today = date.today()

    total_companies = procurements.count()
    products_supplied = procurements.count()

    purchases_this_month = procurements.filter(
        actual_delivery_date__year=today.year,
        actual_delivery_date__month=today.month
    ).aggregate(total=Sum('total_cost'))['total'] or 0

    pending_orders = procurements.filter(actual_delivery_date__isnull=True).count()
    
    paginator = Paginator(procurements, 10)  # 10 sales per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'procurements': page_obj,
        'total_companies': total_companies,
        'products_supplied': products_supplied,
        'purchases_this_month': purchases_this_month,
        'pending_orders': pending_orders,
        'page_obj': page_obj,
        'selected_dealer': supplier_filter,
        'dealer_names': dealer_names
    }
    return render(request, 'core/procurement.html', context)

#adding procurements 
@login_required
def add_procurement(request):
    if request.method == 'POST':
        form = ProcurementForm(request.POST)
        if form.is_valid():
            procurement = form.save()

            min_qty = form.cleaned_data.get('minimum_quantity') or 10  # fallback to 10 if not set
            # After saving procurement, update inventory
            '''when get_or_create() is called, Django uses 
            this constraint (class Meta:unique_together = ('produce', 'branch'))
            to avoid duplicates.'''
            inventory, created = Inventory.objects.get_or_create(
                produce=procurement.produce,
                branch=procurement.branch,
                defaults={'quantity': 0, 'minimum_quantity': min_qty}
            )
            
            #This automatically updates the quantity in the inventory avoiding duplicates
            inventory.quantity += procurement.quantity
            inventory.save()

            return redirect('procurement_list')  # Or anywhere you want
    
    form = ProcurementForm()

    produces = Produce.objects.select_related('dealer')
    produce_info = {
        str(p.id): {
            'dealer': p.dealer.id,
            'dealer_name': p.dealer.name,
            'cost_per_unit': float(p.buying_price)
        }
        for p in produces
    }
    return render(request, 'core/add_procurement.html', {'form': form, 'produce_data': json.dumps(produce_info, cls=DjangoJSONEncoder),})

#editing procurements
@login_required
def edit_procurement(request, pk):
    user = request.user
    if user.user_type == 'admin':
        procurement = Procurement.objects.get(pk=pk)
    else:
        procurement = Procurement.objects.get(pk=pk, branch=user.branch) 
    if request.method == 'POST':
        form = ProcurementForm(request.POST, instance=procurement)
        if form.is_valid():
            form.save()
            return redirect('/procurement/')
    else:
        form = ProcurementForm(instance=procurement)
    return render(request, 'core/edit_procurement.html', {'form': form, 'procurement':procurement })

def view_procurement(request, pk):
    user = request.user
    if user.user_type == 'admin':
        supply = Procurement.objects.get(pk=pk)
    else:
        supply = Procurement.objects.get(pk=pk, branch=user.branch) 


    return render(request, 'core/view_procure.html', {'supply': supply})
@login_required
def receipt_procurement(request, pk):
    supply = Procurement.objects.get(pk=pk)

    return render(request, 'core/receipt_procure.html', {'supply': supply})

#deleting procurements
@login_required
def delete_procurement(request, pk):
    procurement = Procurement.objects.get(pk=pk)
    if request.method == 'POST':
        procurement.delete()
        return redirect('procurement_list')
    return render(request, 'core/confirm_delete_procurement.html', {'procurement': procurement})

@login_required
def viewstock(request):
    user = request.user
    selected_status = request.GET.get('status', 'all')

    # Base queryset
    if user.user_type == 'admin':
        stock_queryset = Inventory.objects.select_related('produce', 'branch')
    else:
        stock_queryset = Inventory.objects.select_related('produce', 'branch').filter(branch=user.branch)

    # Apply Python-level status filtering (because stock_status is not a DB field)
    if selected_status != 'all':
        filtered_stock = [item for item in stock_queryset if item.stock_status() == selected_status]
    else:
        filtered_stock = list(stock_queryset)

    # Totals
    if user.user_type == 'admin':
        total_products = Procurement.objects.select_related('produce', 'branch', 'dealer').count()
        total_quantity = sum([item.quantity for item in filtered_stock])
        total_stock = len(filtered_stock)
        low_stock_count = stock_queryset.filter(quantity__lt=F('minimum_quantity')).count()
        out_of_stock_count = stock_queryset.filter(quantity=0).count()
    else:
        total_products = Procurement.objects.select_related('produce', 'branch', 'dealer').filter(branch=user.branch).count()
        total_quantity = sum([item.quantity for item in filtered_stock])
        total_stock = len(filtered_stock)
        low_stock_count = stock_queryset.filter(quantity__lt=F('minimum_quantity')).count()
        out_of_stock_count = stock_queryset.filter(quantity=0).count()

    # Pagination
    paginator = Paginator(filtered_stock, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'stock': page_obj,
        'page_obj': page_obj,
        'total_stock': total_stock,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_quantity': total_quantity,
        'selected_status': selected_status,
    }
    return render(request, 'core/viewstock.html', context)


#This view is for payments
@login_required
def payments_list(request):
    user = request.user
    status_filter = request.GET.get('status', 'all')  # New filter

    # Base queryset
    if user.user_type == 'admin':
        sales_queryset = Sale.objects.all()
    else:
        sales_queryset = Sale.objects.filter(branch=user.branch)

    # Apply filter
    if status_filter == 'complete':
        sales_queryset = sales_queryset.filter(is_paid=True)
    elif status_filter == 'pending':
        sales_queryset = sales_queryset.filter(is_paid=False)

    # Stats
    total_payments = sum(
        [sale.total_amount for sale in sales_queryset if sale.amount_received >= sale.total_amount],
        Decimal('0.00')
    )
    todays_payments = sum(
        [sale.total_amount for sale in sales_queryset if sale.sale_date.date() == date.today() and sale.amount_received >= sale.total_amount],
        Decimal('0.00')
    )
    outstanding = sum(
        [sale.total_amount - sale.amount_received for sale in sales_queryset if sale.amount_received < sale.total_amount],
        Decimal('0.00')
    )

    # Pagination
    paginator = Paginator(sales_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Optional search query (you may choose to update this too)
    query = request.GET.get('search')
    payments = sales_queryset
    if query:
        payments = payments.filter(
            Q(payment_method__icontains=query) |
            Q(produce__name__icontains=query) |
            Q(customer_name__icontains=query)
        )

    context = {
        'sales': page_obj,
        'page_obj': page_obj,
        'payments': payments,
        'total_payments': total_payments,
        'outstanding': outstanding,
        'todays_payments': todays_payments,
        'selected_status': status_filter,  # Important for keeping the dropdown selection
    }
    return render(request, 'core/payments.html', context)


@login_required
def payment_details(request, pk):
    #gets the selected sale
    user = request.user
    if user.user_type == 'admin':
        payments = Sale.objects.get(pk=pk)
 
    else:
        payments = Sale.objects.get(pk=pk, branch=user.branch)

    outstanding = payments.total_amount - payments.amount_received    

    return render(request, 'core/payment_details.html', {'payments': payments, 'outstanding':outstanding })

@login_required
def pay_receipt (request, pk):
    user = request.user
    if user.user_type == 'admin':
        payments = Sale.objects.get(pk=pk)
 
    else:
        payments = Sale.objects.get(pk=pk, branch=user.branch)

    outstanding = payments.total_amount - payments.amount_received  
    return render (request, 'core/pay_receipt.html', {'payments': payments, 'outstanding':outstanding })
@login_required
def edit_payments (request, pk):
    user = request.user
    if user.user_type == 'admin':
        payments = Sale.objects.get(pk=pk)
    else:
        payments = Sale.objects.get(pk=pk, branch=user.branch)

    sale = get_object_or_404(Sale, pk=pk)

    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            updated_sale = form.save(commit=False)
            updated_sale.sales_agent = request.user
            updated_sale.branch = request.user.branch

            try:
                inventory = Inventory.objects.get(produce=updated_sale.produce, branch=updated_sale.branch)
            except Inventory.DoesNotExist:
                messages.error(request, "Inventory not found for this produce and branch.")
                return redirect('payments_list', pk=pk)

            # Calculate quantity difference
            quantity_diff = updated_sale.quantity - sale.quantity

            # Check if enough stock is available if quantity increased
            if quantity_diff > 0 and inventory.quantity < quantity_diff:
                messages.error(request, f"Only {inventory.quantity} kg in stock. Cannot increase sale.")
                return redirect('payments_list', pk=pk)

            # Adjust inventory
            inventory.quantity -= quantity_diff
            inventory.save()
            updated_sale.save()

            messages.success(request, "Payment updated successfully.")
            return redirect('payments_list')
    else:
        form = SaleForm(instance=sale)
    produces = Produce.objects.all()
    produce_data = {str(p.id): float(p.selling_price) for p in produces}
    return render (request, 'core/editpayments.html', {'payments': payments, 'form': form , 'produce_prices': json.dumps(produce_data, cls=DjangoJSONEncoder)})

@login_required
def sales_list(request):
    user = request.user
    if user.user_type == 'admin':
        sales = Sale.objects.select_related('produce', 'branch', 'sales_agent').all()
    else:
        sales = Sale.objects.select_related('produce', 'branch', 'sales_agent').filter(branch=user.branch)

    product_filter = request.GET.get('product')
    if product_filter and product_filter != "all":
        sales = sales.filter(produce__name=product_filter)


     # 🛠 New Sales Summary Logic
    today = date.today()

    sales_today = sales.filter(sale_date__date=today).count()

# Total number of sales made this month
    sales_this_month = sales.filter(
        sale_date__year=today.year,
        sale_date__month=today.month
    ).count()

    # Average daily sales in the current month
    # Count days with at least one sale (optional) or use today.day for total days passed
    average_daily_sales = round(sales_this_month / today.day, 2) if today.day else 0

    # Get all unique product names for the dropdown
    product_names = sales.values_list('produce__name', flat=True).distinct()

    #permissions for salesagent denied
    can_edit = True  # Default

    if user.user_type == 'sales_agent':
        can_edit = False  # Sales Agent cannot edit or delete

    #pagination
    paginator = Paginator(sales, 10)  # 10 sales per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'sales': page_obj,
        'product_names': product_names,
        'selected_product': product_filter,
        'page_obj': page_obj,
        'sales_today': sales_today,
        'sales_this_month': sales_this_month,
        'average_daily_sales': average_daily_sales,
        'can_edit':can_edit
    }

    return render(request, 'core/sales.html', context)

@login_required
def view_sale(request, pk):
    user = request.user
    if user.user_type == 'admin':
        sales = Sale.objects.get(pk=pk)
    else:
        sales = Sale.objects.get(pk=pk, branch=user.branch)
    outstanding = sales.total_amount - sales.amount_received
    return render(request, 'core/viewsales.html', {'sales': sales, 'outstanding':outstanding})

@login_required
def sale_receipt(request, pk):
    user = request.user
    if user.user_type == 'admin':
        sales = Sale.objects.get(pk=pk)
    else:
        sales = Sale.objects.get(pk=pk, branch=user.branch)
    outstanding = sales.total_amount - sales.amount_received
    return render(request, 'core/sale_receipt.html', {'sales': sales, 'outstanding':outstanding})

@login_required
def add_sale(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)

            # Attach current user and branch
            sale.sales_agent = request.user
            sale.branch = request.user.branch

            # Fetch the inventory record
            try:
                inventory = Inventory.objects.get(
                    produce=sale.produce, branch=sale.branch
                )
            except Inventory.DoesNotExist:
                messages.error(request, "Inventory not found for this produce and branch.")
                return redirect('add_sale')

            # Check stock availability
            if sale.quantity > inventory.quantity:
                messages.error(request, f"Only {inventory.quantity} kg in stock.")
                return redirect('/sales/add/')

            # Deduct quantity and save
            inventory.quantity -= sale.quantity
            inventory.save()

            sale.save()
            messages.success(request, "Sale recorded successfully.")
            return redirect('/sales/')  # or another success page
    else:
        form = SaleForm()

    produces = Produce.objects.all()
    produce_data = {str(p.id): float(p.selling_price) for p in produces}
    return render(request, 'core/add_sales.html', {'form': form, 'produce_prices': json.dumps(produce_data, cls=DjangoJSONEncoder)})

@login_required
def delete_sale(request, pk):
    user = request.user
    if user.user_type == 'admin':
        sales = Sale.objects.get(pk=pk)
    else:
        sales = Sale.objects.get(pk=pk, branch=user.branch)
    return render(request, 'core/delete_sales.html', {'sales': sales})

@login_required
def edit_sale(request, pk):
    user = request.user
    if user.user_type == 'admin':
        sales = Sale.objects.get(pk=pk)
    else:
        sales = Sale.objects.get(pk=pk, branch=user.branch)

    sale = get_object_or_404(Sale, pk=pk)

    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            updated_sale = form.save(commit=False)
            updated_sale.sales_agent = request.user
            updated_sale.branch = request.user.branch

            try:
                inventory = Inventory.objects.get(produce=updated_sale.produce, branch=updated_sale.branch)
            except Inventory.DoesNotExist:
                messages.error(request, "Inventory not found for this produce and branch.")
                return redirect('edit_sale', pk=pk)

            # Calculate quantity difference
            quantity_diff = updated_sale.quantity - sale.quantity

            # Check if enough stock is available if quantity increased
            if quantity_diff > 0 and inventory.quantity < quantity_diff:
                messages.error(request, f"Only {inventory.quantity} kg in stock. Cannot increase sale.")
                return redirect('edit_sale', pk=pk)

            # Adjust inventory
            inventory.quantity -= quantity_diff
            inventory.save()
            updated_sale.save()

            messages.success(request, "Sale updated successfully.")
            return redirect('sales_list')
    else:
        form = SaleForm(instance=sale)
    
    produces = Produce.objects.all()
    produce_data = {str(p.id): float(p.selling_price) for p in produces}
    return render(request, 'core/editsale.html', {'sales': sales, 'form':form, 'produce_prices': json.dumps(produce_data, cls=DjangoJSONEncoder)})

@login_required
def reports_view(request):
    sales = Sale.objects.all()

    # 1. Summary Metrics
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = sales.count()
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # 2. Profit Margin (Optional - assuming you have cost_price)
    try:
        total_profit = sum([(sale.selling_price - sale.produce.cost_price) * sale.quantity for sale in sales])
        profit_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
    except:
        profit_margin = 25  # Example default if no cost_price field yet

    # 3. Sales Trend (Monthly)
    sales_per_month = []
    for month in range(1, 13):
        monthly_sales = sales.filter(sale_date__month=month).aggregate(total=Sum('total_amount'))['total'] or 0
        sales_per_month.append(int(monthly_sales))

    # 4. Product Performance
    product_sales = Sale.objects.values('produce__name').annotate(total_sales=Sum('total_amount')).order_by('-total_sales')

    # 5. Top Products
    top_products = product_sales[:3]

    # 6. Recent Transactions
    recent_sales = Sale.objects.order_by('-sale_date')[:5]

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'average_order_value': average_order_value,
        'profit_margin': profit_margin,
        'sales_per_month': sales_per_month,
        'product_sales': product_sales,
        'top_products': top_products,
        'recent_sales': recent_sales,
    }

    return render(request, 'core/reports.html', context)

@login_required
def sales_analytics(request):
    period = request.GET.get('period', 'this_month')

    today = date.today()
    sales = Sale.objects.all()

    # Filter Sales Based on Period
    if period == 'today':
        sales = sales.filter(sale_date__date=today)

    elif period == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        sales = sales.filter(sale_date__date__range=(start_of_week, end_of_week))

    elif period == 'this_month':
        sales = sales.filter(sale_date__year=today.year, sale_date__month=today.month)

    elif period == 'this_year':
        sales = sales.filter(sale_date__year=today.year)

    # Calculations
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    number_of_sales = sales.count()
    average_sales = total_sales / number_of_sales if number_of_sales > 0 else 0
    number_of_customers = sales.values('customer_name').distinct().count()


    # CSV Download
    if 'download' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Sale ID', 'Customer', 'Product', 'Quantity', 'Total Amount', 'Sale Date'])

        for sale in sales:
            writer.writerow([
                sale.id,
                sale.customer_name,
                sale.produce.name,
                sale.quantity,
                sale.total_amount,
                sale.sale_date
            ])

        return response

    context = {
        'sales': sales,
        'total_sales': total_sales,
        'number_of_sales': number_of_sales,
        'average_sales': average_sales,
        'number_of_customers': number_of_customers,
        'selected_period': period,
    }

    return render(request, 'core/sales-analytics.html', context)



def inventory_status(request):
    today = date.today()

    total_inventory_value = Inventory.objects.aggregate(
        total_value=Sum(F('quantity') * F('unit_price'))
    )['total_value'] or 0

    total_items = Inventory.objects.count()

    LOW_inventory_THRESHOLD = 500
    low_inventory_items = Inventory.objects.filter(quantity__lt=LOW_inventory_THRESHOLD).count()

    # Total sales for this month
    sales_value = Sale.objects.filter(
        sale_date__year=today.year,
        sale_date__month=today.month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    average_inventory = total_inventory_value / 2 if total_inventory_value else 1
    inventory_turnover_rate = sales_value / average_inventory

    context = {
        'total_inventory_value': total_inventory_value,
        'total_items': total_items,
        'low_inventory_items': low_inventory_items,
        'inventory_turnover_rate': round(inventory_turnover_rate, 1),
    }

    return render(request, 'core/inventory-status.html', context)


@login_required
def financial_reports(request):
    today = date.today()
    sales = Sale.objects.all()

    # 1. Revenue
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    # 2. COGS (Cost of Goods Sold)
    total_cogs = sum([(sale.quantity * sale.produce.cost_price) for sale in sales]) if sales else 0

    # 3. Gross Profit
    gross_profit = total_revenue - total_cogs

    # Revenue vs Expenses per month
    revenue_per_month = []
    expenses_per_month = []
    gross_profit_per_month = []
    for month in range(1, 13):
        month_revenue = sales.filter(sale_date__month=month).aggregate(total=Sum('total_amount'))['total'] or 0
        
        month_cogs = sum([(sale.quantity * sale.produce.cost_price) for sale in sales.filter(sale_date__month=month)])

        month_gross_profit = month_revenue - month_cogs

        revenue_per_month.append(int(month_revenue))
        
        gross_profit_per_month.append(int(month_gross_profit))
       
    context = {
        'total_revenue': total_revenue,
        'gross_profit': gross_profit,
        'revenue_per_month': revenue_per_month,
        'expenses_per_month': expenses_per_month,
        'gross_profit_per_month': gross_profit_per_month,
    }

    return render(request, 'core/financial-reports.html', context)
