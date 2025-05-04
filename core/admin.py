from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Branch)
admin.site.register(CustomUser)
admin.site.register(Dealer)
admin.site.register(Produce)
admin.site.register(Procurement)
admin.site.register(Inventory)
admin.site.register(Sale)
admin.site.register(Payment)