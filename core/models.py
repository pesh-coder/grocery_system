from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

# --------------------
# Custom User Model
# --------------------
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('sales_agent', 'Sales Agent'),
    ]

    phone_number = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='sales_agent')
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_user_type_display()}"

# --------------------
# Branch Model
# --------------------
class Branch(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --------------------
# Dealer (was Supplier)
# --------------------
class Dealer(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField()
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --------------------
# Produce (was Product)
# --------------------
class Produce(models.Model):
    PRODUCE_TYPE_CHOICES = [
        ('beans', 'Beans'),
        ('maize', 'Maize'),
        ('g-nuts', 'Groundnuts'),
        ('soybeans', 'Soybeans'),
        ('cowpeas', 'Cowpeas'),
    ]

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=100, choices=PRODUCE_TYPE_CHOICES)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    dealer = models.ForeignKey(Dealer, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.type})"

# --------------------
# Procurement
# --------------------
class Procurement(models.Model):
    produce = models.ForeignKey(Produce, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Procurement #{self.id} - {self.produce.name}"
    
    def get_total(self):
        #calculates the total price based on how much was brought in
        return round(self.cost_per_unit * self.quantity, 2)

# --------------------
# Inventory
# --------------------
class Inventory(models.Model):
    produce = models.ForeignKey(Produce, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('produce', 'branch')

    def __str__(self):
        return f"{self.produce.name} at {self.branch.name}"
    
    
    
    def is_low_stock(self):
        return self.quantity < self.minimum_quantity
    
    '''def is_in_stock(self):
        return self.quantity >= self.minimum_quantity
    '''
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.is_low_stock():
            return "Low Stock"
        else:
            return "In Stock"

# --------------------
# Sale (includes credit fields)
# --------------------
class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('credit', 'Credit'),
        ('mobile_money', 'Mobile Money'),
    ]

    produce = models.ForeignKey(Produce, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    amount_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    due_date = models.DateField(null=True, blank=True)
    buyer_national_id = models.CharField(max_length=20, null=True, blank=True)
    buyer_contact = models.CharField(max_length=15, null=True, blank=True)
    customer_name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    sales_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sale_date = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.customer_name}"
    

    


# --------------------
# Payment
# --------------------
class Payment(models.Model):
    PAYMENT_TYPES = [
        ('credit_sale', 'Credit Sale Payment'),
        ('supplier', 'Supplier Payment'),
        ('other', 'Other Payment'),
    ]
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100)  # Can be sale ID, supplier ID, etc.
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.payment_type} Payment - UGX {self.amount}"
