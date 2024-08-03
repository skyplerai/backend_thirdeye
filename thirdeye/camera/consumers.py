# camera/consumers.py

import json
import asyncio
import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import CameraStream
from .face_recognition_module import FaceRecognitionProcessor
import logging

logger = logging.getLogger(__name__)

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info('WebSocket connection requested')
        self.stream_id = self.scope['url_route']['kwargs']['stream_id']
        logger.info(f'Stream ID: {self.stream_id}')
        self.stop_stream = False
        await self.accept()
        logger.info(f'WebSocket connection established for stream ID: {self.stream_id}')
        
        # Initialize face recognition processor
        self.face_processor = FaceRecognitionProcessor()
        
        # Start the stream in a separate task
        asyncio.create_task(self.start_stream())

    async def disconnect(self, close_code):
        logger.info(f'WebSocket disconnected with code {close_code}')
        self.stop_stream = True

    async def receive(self, text_data):
        logger.info(f'Received data: {text_data}')
        data = json.loads(text_data)
        if data.get('command') == 'stop_stream':
            logger.info('Stop stream command received')
            self.stop_stream = True

    async def start_stream(self):
        try:
            # Retrieve the camera stream object
            stream = await sync_to_async(CameraStream.objects.get)(id=self.stream_id)
            logger.info(f'Retrieved stream: {stream}')

            # Open the video capture
            cap = cv2.VideoCapture(stream.stream_url)
            logger.info(f'Opened video capture for URL: {stream.stream_url}')

            while not self.stop_stream:
                ret, frame = cap.read()
                if not ret:
                    logger.warning('Failed to capture frame')
                    await asyncio.sleep(0.1)
                    continue

                # Process the frame
                processed_frame, detected_faces = await self.process_frame(frame)

                # Encode frame to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')

                # Send frame and detected faces to client
                await self.send(text_data=json.dumps({
                    'frame': base64_frame,
                    'detected_faces': detected_faces,
                }))

                # Control the frame rate
                await asyncio.sleep(0.033)  # Approx. 30 FPS

        except Exception as e:
            logger.error(f'Error in start_stream: {str(e)}')
            await self.send(text_data=json.dumps({'error': str(e)}))
        finally:
            if 'cap' in locals():
                cap.release()
            logger.info('Closing WebSocket connection')
            await self.close()

    async def process_frame(self, frame):
        # Process the frame using the face recognition module
        processed_frame, detected_faces = await self.face_processor.process_frame(frame)
        return processed_frame, detected_faces