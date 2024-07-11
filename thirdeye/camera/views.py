from django.shortcuts import render
from notifications.models import Notification
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import StaticCamera, DDNSCamera, CameraStream, Face
from .serializers import StaticCameraSerializer, DDNSCameraSerializer, CameraStreamSerializer, FaceSerializer, RenameFaceSerializer, RenameCameraSerializer
from rest_framework import status, generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .pagination import DynamicPageSizePagination

class StaticCameraView(generics.GenericAPIView):
    serializer_class = StaticCameraSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=StaticCameraSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            static_camera = StaticCamera.objects.create(user=request.user, **serializer.validated_data)
            CameraStream.objects.create(user=request.user, camera=static_camera, stream_url=static_camera.rtsp_url())
            return Response({"message": "Static camera details saved successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DDNSCameraView(generics.GenericAPIView):
    serializer_class = DDNSCameraSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=DDNSCameraSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            ddns_camera = DDNSCamera.objects.create(user=request.user, **serializer.validated_data)
            CameraStream.objects.create(user=request.user, ddns_camera=ddns_camera, stream_url=ddns_camera.rtsp_url())
            return Response({"message": "DDNS camera details saved successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetStreamURLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, camera_type):
        try:
            if camera_type == 'static':
                cameras = StaticCamera.objects.filter(user=request.user)
            else:
                cameras = DDNSCamera.objects.filter(user=request.user)
                
            stream_urls = []
            for camera in cameras:
                streams = CameraStream.objects.filter(user=request.user, camera=camera if camera_type == 'static' else None, ddns_camera=camera if camera_type != 'static' else None)
                for stream in streams:
                    stream_urls.append(stream.stream_url)
                    
            return Response({"stream_urls": stream_urls}, status=status.HTTP_200_OK)
        except (StaticCamera.DoesNotExist, DDNSCamera.DoesNotExist):
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

class FaceView(generics.GenericAPIView):
    serializer_class = FaceSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            face = serializer.save(user=request.user)
            response_serializer = self.serializer_class(face)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RenameFaceView(generics.GenericAPIView):
    serializer_class = RenameFaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Face.objects.all()

    def patch(self, request, pk):
        try:
            face = Face.objects.get(pk=pk)
        except Face.DoesNotExist:
            return Response({"error": "Face not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(face, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Face renamed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DetectedFacesView(generics.ListAPIView):
    serializer_class = FaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPageSizePagination

    def get_queryset(self):
        queryset = Face.objects.filter(user=self.request.user).order_by('-created_at')
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(created_at__date=date)
        return queryset

class RenameCameraView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='New name of the camera'),
            },
        ),
        responses={200: 'OK', 400: 'Bad Request', 404: 'Not Found'},
    )
    def patch(self, request, camera_type, pk):
        name = request.data.get('name')
        if not name:
            return Response({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        if camera_type == 'static':
            try:
                camera = StaticCamera.objects.get(pk=pk)
            except StaticCamera.DoesNotExist:
                return Response({"error": "Static Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        elif camera_type == 'ddns':
            try:
                camera = DDNSCamera.objects.get(pk=pk)
            except DDNSCamera.DoesNotExist:
                return Response({"error": "DDNS Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Invalid camera type"}, status=status.HTTP_400_BAD_REQUEST)

        camera.name = name
        camera.save()

        return Response({"message": "Camera renamed successfully"}, status=status.HTTP_200_OK)

class NotificationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all notifications for the authenticated user",
        responses={
            200: openapi.Response(
                description="List of notifications",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "verb": "Face Detected",
                            "description": "John Doe detected in camera 1 at 12:34 PM, view in database",
                            "timestamp": "2023-07-06T12:34:56Z"
                        },
                        {
                            "id": 2,
                            "verb": "Face Detected",
                            "description": "Jane Doe detected in camera 2 at 12:35 PM, view in database",
                            "timestamp": "2023-07-06T12:35:56Z"
                        }
                    ]
                }
            ),
            401: "Unauthorized"
        }
    )
    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        notification_data = [
            {
                "id": n.id,
                "verb": n.verb,
                "description": n.description,
                "timestamp": n.timestamp.strftime('%Y-%m-%dT%H:%M:%S')
            } for n in notifications
        ]
        return Response(notification_data, status=200)    
