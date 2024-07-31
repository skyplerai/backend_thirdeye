# camera/consumers.py

import json
import cv2
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import CameraStream, Face
from .face_recognition_module import process_frame

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        self.stop_stream = False
        await self.accept()
        await self.start_stream()

    async def disconnect(self, close_code):
        self.stop_stream = True

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('command') == 'stop_stream':
            self.stop_stream = True

    async def start_stream(self):
        stream = await sync_to_async(CameraStream.objects.get)(id=self.stream_id)
        cap = cv2.VideoCapture(stream.stream_url)
        
        try:
            while not self.stop_stream:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame (face detection)
                processed_frame, detected_faces, detection_time = await sync_to_async(process_frame)(frame)
                
                # Encode frame to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                
                # Save detected faces
                for face_data in detected_faces:
                    await self.save_face(face_data)  # Changed: Removed sync_to_async here
                
                # Send frame and detected faces to client
                await self.send(text_data=json.dumps({
                    'frame': base64_frame,
                    'detected_faces': detected_faces,
                    'detection_time': detection_time
                }))
        finally:
            cap.release()
            await self.close()

    @sync_to_async
    def save_face(self, face_data):
        face, created = Face.objects.get_or_create(
            name=face_data['name'],
            defaults={'embedding': face_data['embedding']}
        )
        if created:
            face.image.save(f"{face.name}.jpg", base64.b64decode(face_data['image']))