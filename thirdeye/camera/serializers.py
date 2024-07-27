#camera/serializers.py
from rest_framework import serializers
from .models import StaticCamera, DDNSCamera, CameraStream, TempFace, PermFace

class TempFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TempFace
        fields = ['id', 'face_id', 'timestamp']

class PermFaceSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PermFace
        fields = ['id', 'name', 'last_seen', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image_paths and request is not None:
            return request.build_absolute_uri(obj.image_paths[0])
        return None
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