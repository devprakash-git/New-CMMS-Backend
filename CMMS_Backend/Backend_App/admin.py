from django.contrib import admin
from .models import (
    CustomUser, Hall, Item, RebateApp, Feedback, 
    Cart, Booking, MyBooking, QRDatabase, Menu, Notification, DailyRebateRefund, FixedCharges
)

# Register your models here.
admin.site.site_header = "CMMS Admin"
admin.site.site_title = "CMMS Admin"
admin.site.index_title = "CMMS Admin"
admin.site.register(CustomUser)
admin.site.register(Hall)
admin.site.register(Item)
admin.site.register(RebateApp)
admin.site.register(Feedback)
admin.site.register(Cart)
admin.site.register(Booking)
admin.site.register(MyBooking)
admin.site.register(QRDatabase)
admin.site.register(Menu)
admin.site.register(Notification)
admin.site.register(DailyRebateRefund)
admin.site.register(FixedCharges)

