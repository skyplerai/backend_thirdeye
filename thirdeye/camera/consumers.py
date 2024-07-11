import base64
import cv2
import json
import numpy as np
import threading
from channels.generic.websocket import WebsocketConsumer
from .face_recognition_module import process_frame
from django.contrib.auth import get_user_model
from notifications.signals import notify
from .models import StaticCamera, DDNSCamera

User = get_user_model()

class CameraConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        self.camera_url = self.scope['url_route']['kwargs']['camera_url']
        self.capture_thread = threading.Thread(target=self.stream_camera)
        self.capture_thread.start()

    def disconnect(self, close_code):
        if self.capture_thread.is_alive():
            self.capture_thread.join()

    def stream_camera(self):
        cap = cv2.VideoCapture(self.camera_url)
        if not cap.isOpened():
            self.send(text_data=json.dumps({"error": "Failed to open camera stream"}))
            return
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            try:
                frame, detected_faces, detection_time = process_frame(frame)
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                response = {
                    "frame": frame_base64,
                    "detected_faces": detected_faces,
                    "detection_time": detection_time
                }
                self.send(text_data=json.dumps(response))
                
                # Notify users about detected faces
                camera_name = self.get_camera_name(self.camera_url)
                for face in detected_faces:
                    detection_time_str = detection_time
                    notification_message = f"{face['name']} detected in {camera_name} at {detection_time_str}, view in database"
                    notify.send(self.scope["user"], recipient=self.scope["user"], verb="Face Detected", description=notification_message)

            except Exception as e:
                self.send(text_data=json.dumps({"error": str(e)}))
                break
        
        cap.release()

    def get_camera_name(self, camera_url):
        try:
            static_camera = StaticCamera.objects.get(ip_address=camera_url)
            return static_camera.name
        except StaticCamera.DoesNotExist:
            try:
                ddns_camera = DDNSCamera.objects.get(ddns_hostname=camera_url)
                return ddns_camera.name
            except DDNSCamera.DoesNotExist:
                return "Unknown Camera"
