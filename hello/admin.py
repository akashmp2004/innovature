from django.contrib import admin
from .models import SplitGroup, GroupMember, Expense, ExpenseSplit, Settlement

admin.site.register(SplitGroup)
admin.site.register(GroupMember)
admin.site.register(Expense)
admin.site.register(ExpenseSplit)
admin.site.register(Settlement)
