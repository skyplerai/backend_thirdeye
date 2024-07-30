import cv2
import base64
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .face_recognition_module import detect_faces, generate_simple_feature
from .models import StaticCamera, DDNSCamera
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.camera_url = self.scope['url_route']['kwargs']['camera_url']
        self.user = self.scope["user"]
        logger.debug(f"Connecting to camera: {self.camera_url} for user: {self.user}")
        self.cap = await self.get_camera_stream()
        if not self.cap or not self.cap.isOpened():
            logger.error(f"Failed to open camera stream: {self.camera_url}")
            await self.close()
            return
        self.send_frame_task = asyncio.create_task(self.send_frames())
        self.frame_buffer = asyncio.Queue(maxsize=10)
        self.produce_frames_task = asyncio.create_task(self.produce_frames())

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        if hasattr(self, 'cap'):
            await asyncio.to_thread(self.cap.release)
        if hasattr(self, 'send_frame_task'):
            self.send_frame_task.cancel()
        if hasattr(self, 'produce_frames_task'):
            self.produce_frames_task.cancel()

    async def send_frames(self):
        try:
            while True:
                if self.frame_buffer.empty():
                    await asyncio.sleep(0.01)
                    continue

                frame = await self.frame_buffer.get()
                faces = await asyncio.to_thread(detect_faces, frame)
                logger.debug(f"Detected {len(faces)} faces")
                detected_faces = []
                for face in faces:
                    feature = await asyncio.to_thread(generate_simple_feature, face, frame)
                    detected_faces.append({
                        'bbox': face[:4].tolist(),
                        'confidence': face[4],
                        'feature': feature.tolist()
                    })

                _, buffer = cv2.imencode('.jpg', frame)
                base64_frame = base64.b64encode(buffer).decode('utf-8')

                try:
                    await self.send(text_data=json.dumps({
                        'frame': base64_frame,
                        'detected_faces': detected_faces
                    }))
                except Exception as e:
                    logger.error(f"Error sending frame: {str(e)}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Send frames task cancelled")
        except Exception as e:
            logger.error(f"Error in send_frames: {str(e)}")

    async def produce_frames(self):
        try:
            while True:
                ret, frame = await asyncio.to_thread(self.cap.read)
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    await asyncio.sleep(0.1)
                    continue

                if self.frame_buffer.full():
                    await self.frame_buffer.get()
                await self.frame_buffer.put(frame)
                logger.debug("Frame added to buffer")
                await asyncio.sleep(0.033)  # Adjust based on desired frame rate
        except asyncio.CancelledError:
            logger.info("Produce frames task cancelled")
        except Exception as e:
            logger.error(f"Error in produce_frames: {str(e)}")

    @sync_to_async
    def get_camera_stream(self):
        try:
            static_camera = StaticCamera.objects.get(ip_address=self.camera_url)
            logger.debug(f"Found static camera: {static_camera}")
            return cv2.VideoCapture(static_camera.rtsp_url())
        except StaticCamera.DoesNotExist:
            try:
                ddns_camera = DDNSCamera.objects.get(ddns_hostname=self.camera_url)
                logger.debug(f"Found DDNS camera: {ddns_camera}")
                return cv2.VideoCapture(ddns_camera.rtsp_url())
            except DDNSCamera.DoesNotExist:
                logger.error(f"No camera found for URL: {self.camera_url}")
                return None
