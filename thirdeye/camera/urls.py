from django.urls import path
from .views import StaticCameraView, DDNSCameraView, GetStreamURLView, FaceView, RenameFaceView, DetectedFacesView, RenameCameraView, NotificationView

urlpatterns = [
    path('static-camera/', StaticCameraView.as_view(), name='static_camera'),
    path('ddns-camera/', DDNSCameraView.as_view(), name='ddns_camera'),
    path('get-stream-url/<str:camera_type>/', GetStreamURLView.as_view(), name='get_stream_url'),
    path('faces/', FaceView.as_view(), name='face'),
    path('rename-face/<int:pk>/', RenameFaceView.as_view(), name='rename_face'),
    path('detected-faces/', DetectedFacesView.as_view(), name='detected_faces'),
    path('rename-camera/<str:camera_type>/<int:pk>/', RenameCameraView.as_view(), name='rename_camera'),
    path('notifications/', NotificationView.as_view(), name='notifications'),
]
