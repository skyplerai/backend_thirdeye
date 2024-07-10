from django.contrib import admin
from .models import StaticCamera, DDNSCamera, Face, CameraStream

@admin.register(StaticCamera)
class StaticCameraAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'name')

@admin.register(DDNSCamera)
class DDNSCameraAdmin(admin.ModelAdmin):
    list_display = ('user', 'ddns_hostname', 'name')

@admin.register(Face)
class FaceAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'created_at')

@admin.register(CameraStream)
class CameraStreamAdmin(admin.ModelAdmin):
    list_display = ('user', 'stream_url', 'created_at')
