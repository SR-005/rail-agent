from django.db import models
from django.contrib.auth.models import User

class PassengerProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="passengers")
    
    full_name=models.CharField(max_length=100, help_text="Exactly as it appears on ID")
    age=models.IntegerField(null=True, blank=True)
    
    GENDER_CHOICES=[
        ('M','Male'),
        ('F','Female'),
        ('T','Transgender')
    ]
    gender=models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    
    BERTH_CHOICES=[
        ('LB', 'Lower'),
        ('MB', 'Middle'),
        ('UB', 'Upper'),
        ('SL', 'Side Lower'),
        ('SU', 'Side Upper'),
        ('NO', 'No Preference')
    ]
    berth_preference=models.CharField(max_length=2, choices=BERTH_CHOICES, default='NO')

    def __str__(self):
        return f"{self.user.username}'s IRCTC Profile"