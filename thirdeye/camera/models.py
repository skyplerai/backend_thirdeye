#camera/models.py
from django.db import models
from django.conf import settings
import os
from django.utils import timezone

class TempFace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    face_id = models.CharField(max_length=20, unique=True)
    image_paths = models.JSONField(default=list)
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

class PermFace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    embeddings = models.JSONField(default=list)
    image_paths = models.JSONField(default=list)
    last_seen = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.name.startswith("Unknown"):
            max_unknown = PermFace.objects.filter(name__startswith="Unknown", user=self.user).count()
            self.name = f"Unknown{max_unknown + 1:03d}"
        super().save(*args, **kwargs)
        
class StaticCamera(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    name = models.CharField(max_length=255, default="Static Camera")

    def rtsp_url(self):
        return f"rtsp://{self.username}:{self.password}@{self.ip_address}:1024/Streaming/Channels/101"

class DDNSCamera(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ddns_hostname = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    name = models.CharField(max_length=255, default="DDNS Camera")

    def rtsp_url(self):
        return f"rtsp://{self.username}:{self.password}@{self.ddns_hostname}:554/Streaming/Channels/101"

class CameraStream(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    camera = models.ForeignKey(StaticCamera, null=True, blank=True, on_delete=models.CASCADE)
    ddns_camera = models.ForeignKey(DDNSCamera, null=True, blank=True, on_delete=models.CASCADE)
    stream_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)