#camera/consumers.py
import base64
import json
import cv2
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .face_recognition_module import generate_frames
from .models import StaticCamera, DDNSCamera
from asgiref.sync import sync_to_async
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.send_frame_task = asyncio.create_task(self.send_frames())

    async def disconnect(self, close_code):
        if hasattr(self, 'cap'):
            self.cap.release()
        if hasattr(self, 'send_frame_task'):
            self.send_frame_task.cancel()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        if message == 'get_frame':
            await self.send_frame()

    async def send_frames(self):
        try:
            while True:
                frame, detected_faces = await asyncio.to_thread(next, self.frame_generator)
                base64_frame = base64.b64encode(frame).decode('utf-8')
                await self.send(text_data=json.dumps({
                    'frame': base64_frame,
                    'detected_faces': detected_faces
                }))
                await asyncio.sleep(0.033)
        except Exception as e:
            logger.error(f"Error in send_frame: {str(e)}")

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