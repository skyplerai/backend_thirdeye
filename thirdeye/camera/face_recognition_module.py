#camera/face_recognition_module.py
import numpy as np
import cv2
import face_recognition
from .models import Face
import time
import base64
from ultralytics import YOLO
import torch
import os
from django.conf import settings

# Initialize the YOLO model
model_path = os.path.join(settings.BASE_DIR, 'yolov8m-face.pt')
yolo_model = YOLO(model_path)

def detect_faces(frame):
    results = yolo_model(frame)
    return results[0].boxes.data.cpu().numpy()

def recognize_face(face_encoding, known_face_encodings, known_face_names):
    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
    name = "Unknown"
    if True in matches:
        first_match_index = matches.index(True)
        name = known_face_names[first_match_index]
    return name

def process_frame(frame):
    start_time = time.time()
    
    # Fetch known faces from the database
    known_faces = Face.objects.all()
    known_face_encodings = [np.frombuffer(face.embedding, dtype=np.float64) for face in known_faces]
    known_face_names = [face.name for face in known_faces]
    
    # Use YOLO to detect faces
    detected_faces = detect_faces(frame)
    
    processed_faces = []
    for face in detected_faces:
        x1, y1, x2, y2, conf, _ = face
        if conf < 0.5:  # confidence threshold
            continue
        
        face_img = frame[int(y1):int(y2), int(x1):int(x2)]
        rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Use face_recognition for encoding
        face_encodings = face_recognition.face_encodings(rgb_face)
        if face_encodings:
            face_encoding = face_encodings[0]
            name = recognize_face(face_encoding, known_face_encodings, known_face_names)
            
            if name == "Unknown":
                face_base64 = base64.b64encode(face_encoding.tobytes()).decode('utf-8')
                _, buffer = cv2.imencode('.jpg', face_img)
                face_image_base64 = base64.b64encode(buffer).decode('utf-8')
                processed_faces.append({
                    "name": name,
                    "embedding": face_base64,
                    "image": face_image_base64,
                    "coordinates": {"top": int(y1), "right": int(x2), "bottom": int(y2), "left": int(x1)}
                })
            
            # Draw rectangle and name on the frame
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
            cv2.rectangle(frame, (int(x1), int(y2) - 35), (int(x2), int(y2)), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (int(x1) + 6, int(y2) - 6), font, 1.0, (255, 255, 255), 1)
    
    end_time = time.time()
    detection_time = time.strftime('%I:%M %p', time.localtime(end_time))
    return frame, processed_faces, detection_time