from django.db import models
import uuid

# Create your models here.
class Member(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    username = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.username

class CustomSession(models.Model):
    user = models.ForeignKey(Member, on_delete=models.CASCADE)
    usertype = models.CharField(max_length=100)
    userdata = models.JSONField()
    jwttoken = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session for {self.user.username}"