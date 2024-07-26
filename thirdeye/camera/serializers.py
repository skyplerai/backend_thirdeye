#camera/serializers.py
from rest_framework import serializers
from .models import StaticCamera, DDNSCamera, CameraStream, TempFace, PermFace

class TempFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TempFace
        fields = ['id', 'face_id', 'timestamp']

class PermFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermFace
        fields = ['id', 'name', 'last_seen']

class RenameFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermFace
        fields = ['name']

class StaticCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticCamera
        fields = ['ip_address', 'username', 'password', 'name']

class DDNSCameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DDNSCamera
        fields = ['ddns_hostname', 'username', 'password', 'name']

class CameraStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraStream
        fields = ['stream_url']