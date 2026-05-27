from django.db import models


class ApiRequestCount(models.Model):
    api_category = models.CharField(max_length=64)
    api_name = models.CharField(max_length=128)
    request_count = models.IntegerField(default=0)
    last_username = models.CharField(max_length=150, default="")
    last_path = models.CharField(max_length=512, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("api_category", "api_name")
        ordering = ("api_category", "api_name")

    def __str__(self):
        return "{}-{}".format(self.api_category, self.api_name)

    def to_dict(self):
        return {
            "api_category": self.api_category,
            "api_name": self.api_name,
            "request_count": self.request_count,
            "last_username": self.last_username,
            "last_path": self.last_path,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class UserBehaviorEvent(models.Model):
    username = models.CharField(max_length=150, default="anonymous")
    api_category = models.CharField(max_length=64)
    api_name = models.CharField(max_length=128)
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=512)
    status_code = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["api_category", "api_name"]),
            models.Index(fields=["username", "created_at"]),
        ]

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "api_category": self.api_category,
            "api_name": self.api_name,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
