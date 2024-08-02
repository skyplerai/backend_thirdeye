# camera/views.py
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
        print('StaticCameraView.post: Received POST request with data:', request.data)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            print('StaticCameraView.post: Serializer is valid')
            static_camera = StaticCamera.objects.create(user=request.user, **serializer.validated_data)
            print('StaticCameraView.post: Created StaticCamera:', static_camera)
            CameraStream.objects.create(user=request.user, camera=static_camera, stream_url=static_camera.rtsp_url())
            print('StaticCameraView.post: Created CameraStream for StaticCamera')
            return Response({"message": "Static camera details saved successfully"}, status=status.HTTP_201_CREATED)
        print('StaticCameraView.post: Serializer errors:', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DDNSCameraView(generics.GenericAPIView):
    serializer_class = DDNSCameraSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=DDNSCameraSerializer)
    def post(self, request):
        print('DDNSCameraView.post: Received POST request with data:', request.data)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            print('DDNSCameraView.post: Serializer is valid')
            ddns_camera = DDNSCamera.objects.create(user=request.user, **serializer.validated_data)
            print('DDNSCameraView.post: Created DDNSCamera:', ddns_camera)
            CameraStream.objects.create(user=request.user, ddns_camera=ddns_camera, stream_url=ddns_camera.rtsp_url())
            print('DDNSCameraView.post: Created CameraStream for DDNSCamera')
            return Response({"message": "DDNS camera details saved successfully"}, status=status.HTTP_201_CREATED)
        print('DDNSCameraView.post: Serializer errors:', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GetStreamURLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, camera_type):
        print('GetStreamURLView.get: Received GET request with camera_type:', camera_type)
        try:
            if camera_type == 'static':
                cameras = StaticCamera.objects.filter(user=request.user)
                print('GetStreamURLView.get: Retrieved StaticCameras:', cameras)
            elif camera_type == 'ddns':
                cameras = DDNSCamera.objects.filter(user=request.user)
                print('GetStreamURLView.get: Retrieved DDNSCameras:', cameras)
            else:
                print('GetStreamURLView.get: Invalid camera type')
                return Response({"error": "Invalid camera type"}, status=status.HTTP_400_BAD_REQUEST)

            if not cameras.exists():
                print(f'GetStreamURLView.get: No {camera_type} cameras found')
                return Response({"error": f"No {camera_type} cameras found"}, status=status.HTTP_404_NOT_FOUND)

            stream_urls = []
            for camera in cameras:
                streams = CameraStream.objects.filter(
                    Q(user=request.user),
                    Q(camera=camera) if camera_type == 'static' else Q(ddns_camera=camera)
                )
                print(f'GetStreamURLView.get: Retrieved streams for {camera_type} camera {camera.id}:', streams)
                for stream in streams:
                    ws_url = f"ws://{request.get_host()}/ws/camera/{stream.id}/"
                    stream_urls.append({
                        "id": stream.id,
                        "name": camera.name,
                        "url": ws_url
                    })
                    print(f'GetStreamURLView.get: Appended stream URL for stream {stream.id}:', ws_url)

            if not stream_urls:
                print('GetStreamURLView.get: No stream URLs found for the given cameras')
                return Response({"error": "No stream URLs found for the given cameras"}, status=status.HTTP_404_NOT_FOUND)

            print('GetStreamURLView.get: Returning stream URLs:', stream_urls)
            return Response({"stream_urls": stream_urls}, status=status.HTTP_200_OK)

        except Exception as e:
            print('GetStreamURLView.get: Exception occurred:', str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class FaceView(generics.ListAPIView):
    serializer_class = PermFaceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPageSizePagination

    def get_queryset(self):
        print('FaceView.get_queryset: Building queryset for PermFace')
        queryset = PermFace.objects.filter(user=self.request.user).order_by('-last_seen')
        date = self.request.query_params.get('date')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        if date and month and year:
            print(f'FaceView.get_queryset: Filtering by date: {date}, month: {month}, year: {year}')
            queryset = queryset.filter(
                Q(last_seen__day=date) &
                Q(last_seen__month=month) &
                Q(last_seen__year=year)
            )
        print('FaceView.get_queryset: Returning queryset:', queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        print('FaceView.list: Received list request')
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            for face in data:
                if face['image_paths']:
                    face['image_url'] = request.build_absolute_uri(face['image_paths'][0])
                    print('FaceView.list: Added image_url to face:', face)
            print('FaceView.list: Returning paginated response')
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        print('FaceView.list: Returning response with serialized data')
        return Response(serializer.data)

class RenameFaceView(generics.UpdateAPIView):
    queryset = PermFace.objects.all()
    serializer_class = RenameFaceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        print('RenameFaceView.get_object: Getting PermFace object with pk:', self.kwargs['pk'])
        obj = get_object_or_404(PermFace, pk=self.kwargs['pk'], user=self.request.user)
        print('RenameFaceView.get_object: Found PermFace object:', obj)
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
        print(f'RenameCameraView.patch: Received PATCH request for {camera_type} camera with pk {pk}')
        name = request.data.get('name')
        if not name:
            print('RenameCameraView.patch: Missing name in request data')
            return Response({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        if camera_type == 'static':
            try:
                camera = StaticCamera.objects.get(pk=pk, user=request.user)
                print('RenameCameraView.patch: Found StaticCamera:', camera)
            except StaticCamera.DoesNotExist:
                print('RenameCameraView.patch: StaticCamera not found')
                return Response({"error": "Static Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        elif camera_type == 'ddns':
            try:
                camera = DDNSCamera.objects.get(pk=pk, user=request.user)
                print('RenameCameraView.patch: Found DDNSCamera:', camera)
            except DDNSCamera.DoesNotExist:
                print('RenameCameraView.patch: DDNSCamera not found')
                return Response({"error": "DDNS Camera not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            print('RenameCameraView.patch: Invalid camera type')
            return Response({"error": "Invalid camera type"}, status=status.HTTP_400_BAD_REQUEST)

        camera.name = name
        camera.save()
        print('RenameCameraView.patch: Camera renamed successfully')

        return Response({"message": "Camera renamed successfully"}, status=status.HTTP_200_OK)
