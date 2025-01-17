from django.contrib import admin
from .models import ProjectResult,Business,CallCenter,Complaint,FinanceRecord

admin.site.register(ProjectResult)
admin.site.register(Business)
admin.site.register(CallCenter)
admin.site.register(Complaint)
admin.site.register(FinanceRecord)
