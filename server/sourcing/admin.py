from django.contrib import admin

from .models import ProductListing, SourcingRequest, Supplier

admin.site.register(SourcingRequest)
admin.site.register(Supplier)
admin.site.register(ProductListing)
