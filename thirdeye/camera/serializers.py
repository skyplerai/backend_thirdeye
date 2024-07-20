#camera/serializers.py
from rest_framework import serializers
from .models import StaticCamera, DDNSCamera, CameraStream, Face
import base64
from django.core.files.base import ContentFile

class FaceSerializer(serializers.ModelSerializer):
    embedding = serializers.CharField()
    image = serializers.CharField(required=False)

    class Meta:
        model = Face
        fields = ['id', 'name', 'embedding', 'created_at', 'image']

    def create(self, validated_data):
        embedding = validated_data.pop('embedding')
        image_data = validated_data.pop('image', None)
        
        face = Face.objects.create(embedding=embedding, **validated_data)

        if image_data:
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            image = ContentFile(base64.b64decode(imgstr), name=f'face_{face.id}.{ext}')
            face.image.save(f'face_{face.id}.{ext}', image, save=True)

        return face

class RenameFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        fields = ['name']

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



class RenameCameraSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
