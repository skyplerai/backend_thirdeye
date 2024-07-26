#camera/consumers.py
import json
import cv2
from channels.generic.websocket import AsyncWebsocketConsumer
from .face_recognition_module import generate_frames
from .models import StaticCamera, DDNSCamera
from asgiref.sync import sync_to_async

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.camera_url = self.scope['url_route']['kwargs']['camera_url']
        self.user = self.scope["user"]
        self.cap = await self.get_camera_stream()
        if not self.cap:
            await self.close()
            return
        
        self.frame_generator = generate_frames(self.cap, self.user)

    async def disconnect(self, close_code):
        if hasattr(self, 'cap'):
            self.cap.release()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        if message == 'get_frame':
            await self.send_frame()

    async def send_frame(self):
        frame, detected_faces = next(self.frame_generator)
        await self.send(text_data=json.dumps({
            'frame': frame.decode('utf-8'),
            'detected_faces': detected_faces
        }))

    @sync_to_async
    def get_camera_stream(self):
        try:
            static_camera = StaticCamera.objects.get(ip_address=self.camera_url)
            return cv2.VideoCapture(static_camera.rtsp_url())
        except StaticCamera.DoesNotExist:
            try:
                ddns_camera = DDNSCamera.objects.get(ddns_hostname=self.camera_url)
                return cv2.VideoCapture(ddns_camera.rtsp_url())
            except DDNSCamera.DoesNotExist:
                return None