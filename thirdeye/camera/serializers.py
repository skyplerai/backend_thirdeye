#camera/serializers.py
from rest_framework import serializers
from .models import StaticCamera, DDNSCamera, CameraStream, Face

class StaticCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticCamera
        fields = ['ip_address', 'username', 'password']

class DDNSCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DDNSCamera
        fields = ['ddns_hostname', 'username', 'password']

class CameraStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraStream
        fields = ['stream_url']

class FaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        fields = ['id', 'name', 'embedding', 'created_at']

class RenameFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        fields = ['name']
