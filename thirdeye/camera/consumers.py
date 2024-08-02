# camera/consumers.py
import json
import cv2
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import CameraStream, PermFace, TempFace
from .face_recognition_module import process_frame

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('CameraConsumer.connect: WebSocket connection requested')
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        print(f'CameraConsumer.connect: Stream ID: {self.stream_id}')
        self.stop_stream = False
        await self.accept()
        print('CameraConsumer.connect: WebSocket connection accepted')
        print(f'CameraConsumer.connect: WebSocket connection established for stream ID: {self.stream_id}')
        await self.start_stream()

    async def disconnect(self, close_code):
        print(f'CameraConsumer.disconnect: WebSocket disconnected with code {close_code}')
        self.stop_stream = True

    async def receive(self, text_data):
        print(f'CameraConsumer.receive: Received data: {text_data}')
        data = json.loads(text_data)
        if data.get('command') == 'stop_stream':
            print('CameraConsumer.receive: Stop stream command received')
            self.stop_stream = True

    async def start_stream(self):
        try:
            print(f'CameraConsumer.start_stream: Starting stream for stream ID: {self.stream_id}')
            stream = await sync_to_async(CameraStream.objects.get)(id=self.stream_id)
            print(f'CameraConsumer.start_stream: Retrieved stream: {stream}')

            # Use cv2.VideoCapture with RTSP transport
            gst_str = ('rtspsrc location={} latency=0 ! '
                       'rtph264depay ! h264parse ! avdec_h264 ! '
                       'videoconvert ! appsink').format(stream.stream_url)
            print(f'CameraConsumer.start_stream: GStreamer pipeline: {gst_str}')
            cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

            if not cap.isOpened():
                print('CameraConsumer.start_stream: Failed to open video stream')
                await self.send(text_data=json.dumps({
                    'error': 'Failed to open video stream'
                }))
                return

            print('CameraConsumer.start_stream: Video stream opened successfully')
            while not self.stop_stream:
                ret, frame = cap.read()
                if not ret:
                    print('CameraConsumer.start_stream: Failed to read frame')
                    break
                
                print('CameraConsumer.start_stream: Frame read successfully')
                # Process frame (face detection)
                processed_frame, detected_faces, detection_time = await sync_to_async(process_frame)(frame, stream.user)
                print(f'CameraConsumer.start_stream: Frame processed, detected_faces: {detected_faces}, detection_time: {detection_time}')
                
                # Encode frame to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')
                print('CameraConsumer.start_stream: Frame encoded to base64')
                
                # Send frame and detected faces to client
                await self.send(text_data=json.dumps({
                    'frame': base64_frame,
                    'detected_faces': detected_faces,
                    'detection_time': detection_time
                }))
                print('CameraConsumer.start_stream: Frame and detected faces sent to client')

        except Exception as e:
            print(f'CameraConsumer.start_stream: Exception occurred: {str(e)}')
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
        finally:
            if 'cap' in locals():
                print('CameraConsumer.start_stream: Releasing video capture')
                cap.release()
            print('CameraConsumer.start_stream: Closing WebSocket connection')
            await self.close()

    @sync_to_async
    def save_face(self, face_data, user):
        print(f'CameraConsumer.save_face: Saving face for user {user}, face_data: {face_data}')
        face, created = PermFace.objects.get_or_create(
            name=face_data['name'],
            user=user,
            defaults={'embeddings': face_data['embedding']}
        )
        if created:
            print('CameraConsumer.save_face: New face created, saving image paths')
            face.image_paths = [face_data['image']]  # Store base64 image
            face.save()
        else:
            print('CameraConsumer.save_face: Face already exists')
