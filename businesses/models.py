from django.db import models
from welcome.views import CustomUser


class Business(models.Model):
    name = models.CharField(max_length=255)
    icon = models.ImageField(upload_to='uploaded_icons/')
    employee_file = models.FileField(upload_to='employee_files/')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='businesses')
    members = models.ManyToManyField(CustomUser, related_name='member_of_businesses')
    category = models.CharField(max_length=200, null=True)

class CallCenter(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='call_centers')
    zip_file = models.FileField(upload_to='call_center_zips/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Call Center for {self.business.name}"
    

class FinanceRecord(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    sold_piece = models.CharField(max_length=255)
    sold_to = models.CharField(max_length=255)
    date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid_price = models.DecimalField(max_digits=10, decimal_places=2)

class Complaint(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    voice = models.FileField(upload_to='complaints/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Complaint from {self.user.email} for {self.business.name}"
    

class ProjectResult(models.Model):
    business_name = models.CharField(max_length=255)
    tasks_and_assignments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.business_name} on {self.created_at}"

