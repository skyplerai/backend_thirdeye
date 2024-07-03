#camera/consumers.py
import base64
import cv2
import json
import numpy as np
import threading
from channels.generic.websocket import WebsocketConsumer
from .face_recognition_module import process_frame

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
                frame, face_names, detection_time = process_frame(frame)
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                response = {
                    "frame": frame_base64,
                    "face_names": face_names,
                    "detection_time": detection_time
                }
                self.send(text_data=json.dumps(response))
            except Exception as e:
                self.send(text_data=json.dumps({"error": str(e)}))
                break
        
        cap.release()
