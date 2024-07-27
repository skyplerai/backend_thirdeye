#camera/views.py
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import StaticCamera, DDNSCamera, CameraStream, TempFace, PermFace
from .serializers import (
    StaticCameraSerializer, DDNSCameraSerializer, CameraStreamSerializer, 
    TempFaceSerializer, PermFaceSerializer, RenameFaceSerializer
)
from .pagination import DynamicPageSizePagination
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404

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

class FaceView(generics.ListAPIView):
    serializer_class = PermFaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPageSizePagination

    def get_queryset(self):
        queryset = PermFace.objects.filter(user=self.request.user).order_by('-last_seen')
        date = self.request.query_params.get('date')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        if date and month and year:
            queryset = queryset.filter(
                Q(last_seen__day=date) &
                Q(last_seen__month=month) &
                Q(last_seen__year=year)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            for face in data:
                if face['image_paths']:
                    face['image_url'] = request.build_absolute_uri(face['image_paths'][0])
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class RenameFaceView(generics.UpdateAPIView):
    queryset = PermFace.objects.all()
    serializer_class = RenameFaceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = get_object_or_404(PermFace, pk=self.kwargs['pk'], user=self.request.user)
        return obj

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
                camera = StaticCamera.objects.get(pk=pk, user=request.user)
            except StaticCamera.DoesNotExist:
                return Response({"error": "Static Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        elif camera_type == 'ddns':
            try:
                camera = DDNSCamera.objects.get(pk=pk, user=request.user)
            except DDNSCamera.DoesNotExist:
                return Response({"error": "DDNS Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Invalid camera type"}, status=status.HTTP_400_BAD_REQUEST)

        camera.name = name
        camera.save()

        return Response({"message": "Camera renamed successfully"}, status=status.HTTP_200_OK)    
    
    