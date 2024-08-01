#camera/consumers.py
import json
import cv2
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import CameraStream, PermFace, TempFace
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
        try:
            stream = await sync_to_async(CameraStream.objects.get)(id=self.stream_id)
            
            # Use cv2.VideoCapture with RTSP transport
            gst_str = ('rtspsrc location={} latency=0 ! '
                       'rtph264depay ! h264parse ! avdec_h264 ! '
                       'videoconvert ! appsink').format(stream.stream_url)
            cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

            if not cap.isOpened():
                await self.send(text_data=json.dumps({
                    'error': 'Failed to open video stream'
                }))
                return

            while not self.stop_stream:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame (face detection)
                processed_frame, detected_faces, detection_time = await sync_to_async(process_frame)(frame, stream.user)
                
                # Encode frame to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame and detected faces to client
                await self.send(text_data=json.dumps({
                    'frame': base64_frame,
                    'detected_faces': detected_faces,
                    'detection_time': detection_time
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
        finally:
            if 'cap' in locals():
                cap.release()
            await self.close()

    @sync_to_async
    def save_face(self, face_data, user):
        face, created = PermFace.objects.get_or_create(
            name=face_data['name'],
            user=user,
            defaults={'embeddings': face_data['embedding']}
        )
        if created:
            face.image_paths = [face_data['image']]  # Store base64 image
            face.save()