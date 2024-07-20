#camera/consumers.py
import base64
import time
import cv2
import json
import numpy as np
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .face_recognition_module import process_frame
from django.contrib.auth import get_user_model
from notifications.signals import notify
from .models import StaticCamera, DDNSCamera
from asgiref.sync import sync_to_async

User = get_user_model()

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.camera_url = self.scope['url_route']['kwargs']['camera_url']
        self.frame_count = 0
        self.last_send_time = 0
        await self.stream_camera()

    async def disconnect(self, close_code):
        pass

    async def stream_camera(self):
        cap = cv2.VideoCapture(self.camera_url)
        if not cap.isOpened():
            await self.send(text_data=json.dumps({"error": "Failed to open camera stream"}))
            return
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            self.frame_count += 1
            if self.frame_count % 5 != 0:  # Process every 5th frame
                continue
            
            current_time = time.time()
            if current_time - self.last_send_time < 0.1:  # Rate limit to 10 FPS
                continue
            
            try:
                frame, detected_faces, detection_time = await sync_to_async(process_frame)(frame)
                _, buffer = cv2.imencode('.webp', frame, [cv2.IMWRITE_WEBP_QUALITY, 80])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                response = {
                    "frame": frame_base64,
                    "detected_faces": detected_faces,
                    "detection_time": detection_time
                }
                await self.send(text_data=json.dumps(response))
                self.last_send_time = current_time
                
                # Notify users about detected faces
                await self.notify_users(detected_faces)
            except Exception as e:
                await self.send(text_data=json.dumps({"error": str(e)}))
                break
        
        cap.release()

    async def notify_users(self, detected_faces):
        camera_name = await self.get_camera_name(self.camera_url)
        for face in detected_faces:
            detection_time_str = time.strftime('%I:%M %p')
            notification_message = f"{face['name']} detected in {camera_name} at {detection_time_str}, view in database"
            await sync_to_async(notify.send)(
                self.scope["user"], 
                recipient=self.scope["user"], 
                verb="Face Detected", 
                description=notification_message
            )

    @staticmethod
    async def get_camera_name(camera_url):
        try:
            static_camera = await sync_to_async(StaticCamera.objects.get)(ip_address=camera_url)
            return static_camera.name
        except StaticCamera.DoesNotExist:
            try:
                ddns_camera = await sync_to_async(DDNSCamera.objects.get)(ddns_hostname=camera_url)
                return ddns_camera.name
            except DDNSCamera.DoesNotExist:
                return "Unknown Camera"