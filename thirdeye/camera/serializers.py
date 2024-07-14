#camera/serializers.py
from rest_framework import serializers
from .models import StaticCamera, DDNSCamera, CameraStream, Face
import numpy as np
import base64

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
    embedding = serializers.CharField(write_only=True)
    embedding_decoded = serializers.SerializerMethodField()
    image = serializers.CharField(write_only=True)

    class Meta:
        model = Face
        fields = ['id', 'name', 'embedding', 'embedding_decoded', 'created_at', 'image']

    def get_embedding_decoded(self, obj):
        try:
            embedding = np.frombuffer(obj.embedding, dtype=np.float64)
            return base64.b64encode(embedding).decode('utf-8')
        except ValueError as e:
            print(f"Error decoding embedding: {e}")
            return ""

    def create(self, validated_data):
        embedding_base64 = validated_data.pop('embedding')
        image_base64 = validated_data.pop('image')
        
        try:
            # Decode the base64 string to binary
            embedding_binary = base64.b64decode(embedding_base64)
            # Decode the base64 string to image binary
            image_binary = base64.b64decode(image_base64)

            # Ensure the binary size is correct for np.float64
            if len(embedding_binary) % 8 != 0:
                raise ValueError("Invalid embedding size")

            # Convert binary embedding to numpy array for validation
            embedding_array = np.frombuffer(embedding_binary, dtype=np.float64)
            print(f"Embedding array shape: {embedding_array.shape}")
            
            # Save the face object with the binary embedding
            face = Face.objects.create(embedding=embedding_binary, **validated_data)

            # Save the image
            with open(f"faces/{face.id}.jpg", "wb") as f:
                f.write(image_binary)

            return face
        except (ValueError, base64.binascii.Error) as e:
            print(f"Error creating face: {e}")
            raise serializers.ValidationError("Invalid embedding or image data")
    
class RenameFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        fields = ['name']

class RenameCameraSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
