from django.db import models


class JobExecutionRecord(models.Model):
    ACTION_SEARCH = "search"
    ACTION_BACKUP = "backup"
    ACTION_PLAN = "plan"
    ACTION_CHOICES = (
        (ACTION_SEARCH, "Search files"),
        (ACTION_BACKUP, "Backup files"),
        (ACTION_PLAN, "Execute plan"),
    )

    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    bk_biz_id = models.IntegerField(default=0)
    bk_host_ids = models.CharField(max_length=512, default="")
    job_plan_id = models.IntegerField(default=0)
    job_instance_id = models.BigIntegerField(default=0)
    job_instance_name = models.CharField(max_length=255, default="")
    step_instance_id = models.BigIntegerField(default=0)
    status = models.IntegerField(default=0)
    status_text = models.CharField(max_length=64, default="unknown")
    search_path = models.CharField(max_length=1024, default="")
    suffix = models.CharField(max_length=64, default="")
    backup_path = models.CharField(max_length=1024, default="")
    job_url = models.CharField(max_length=512, default="")
    result_summary = models.TextField(default="", blank=True)
    error_message = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "bk_biz_id": self.bk_biz_id,
            "bk_host_ids": self.bk_host_ids,
            "job_plan_id": self.job_plan_id,
            "job_instance_id": self.job_instance_id,
            "job_instance_name": self.job_instance_name,
            "step_instance_id": self.step_instance_id,
            "status": self.status,
            "status_text": self.status_text,
            "search_path": self.search_path,
            "suffix": self.suffix,
            "backup_path": self.backup_path,
            "job_url": self.job_url,
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

