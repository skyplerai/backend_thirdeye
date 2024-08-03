import json
import base64
import time
import vlc
import cv2
import numpy as np
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

            print('CameraConsumer.start_stream: Initializing VLC instance')
            instance = vlc.Instance()
            print('CameraConsumer.start_stream: Creating media player')
            player = instance.media_player_new()
            print(f'CameraConsumer.start_stream: Creating media with URL: {stream.stream_url}')
            media = instance.media_new(stream.stream_url)
            print('CameraConsumer.start_stream: Setting media to player')
            player.set_media(media)
            print('CameraConsumer.start_stream: Starting playback')
            player.play()

            print('CameraConsumer.start_stream: Entering stream loop')
            while not self.stop_stream:
                time.sleep(0.1)  # Adjust as needed
                if player.get_state() == vlc.State.Playing:
                    print('CameraConsumer.start_stream: Player is in Playing state')
                    # Get frame from VLC
                    print('CameraConsumer.start_stream: Attempting to get frame from VLC')
                    player.video_take_snapshot(0, 'temp_frame.png', 0, 0)
                    frame = cv2.imread('temp_frame.png')
                    
                    if frame is not None:
                        print('CameraConsumer.start_stream: Frame successfully captured')
                        # Process frame (face detection)
                        print('CameraConsumer.start_stream: Processing frame')
                        processed_frame, detected_faces, detection_time = await sync_to_async(process_frame)(frame, stream.user)
                        print(f'CameraConsumer.start_stream: Frame processed, detected_faces: {detected_faces}, detection_time: {detection_time}')
                        
                        # Encode frame to base64
                        print('CameraConsumer.start_stream: Encoding frame to base64')
                        _, buffer = cv2.imencode('.jpg', processed_frame)
                        base64_frame = base64.b64encode(buffer).decode('utf-8')
                        print('CameraConsumer.start_stream: Frame encoded to base64')
                        
                        # Send frame and detected faces to client
                        print('CameraConsumer.start_stream: Sending frame and detected faces to client')
                        await self.send(text_data=json.dumps({
                            'frame': base64_frame,
                            'detected_faces': detected_faces,
                            'detection_time': detection_time
                        }))
                        print('CameraConsumer.start_stream: Frame and detected faces sent to client')
                    else:
                        print('CameraConsumer.start_stream: Failed to capture frame')
                else:
                    print(f'CameraConsumer.start_stream: Player state: {player.get_state()}')

        except Exception as e:
            print(f'CameraConsumer.start_stream: Exception occurred: {str(e)}')
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
        finally:
            if 'player' in locals():
                print('CameraConsumer.start_stream: Stopping VLC player')
                player.stop()
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