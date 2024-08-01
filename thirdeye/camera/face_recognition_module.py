#camera/face_recognition_module.py
from .models import PermFace
from ultralytics import YOLO
import cv2
import face_recognition
import numpy as np
import base64
import time
import os
from django.conf import settings

# Initialize the YOLO model
model_path = os.path.join(settings.BASE_DIR, 'yolov8m-face.pt')
yolo_model = YOLO(model_path)

def process_frame(frame, user):
    start_time = time.time()
    
    # Fetch known faces from the database
    known_faces = PermFace.objects.filter(user=user)
    known_face_encodings = [np.frombuffer(face.embeddings, dtype=np.float64) for face in known_faces]
    known_face_names = [face.name for face in known_faces]
    
    # Use YOLO to detect faces
    results = yolo_model(frame, conf=0.3)  # Lowered confidence threshold
    
    processed_faces = []
    for result in results:
        boxes = result.boxes.cpu().numpy()
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf)
            
            face_img = frame[y1:y2, x1:x2]
            rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            
            # Use face_recognition for encoding
            face_encodings = face_recognition.face_encodings(rgb_face)
            if face_encodings:
                face_encoding = face_encodings[0]
                name = recognize_face(face_encoding, known_face_encodings, known_face_names)
                
                _, buffer = cv2.imencode('.jpg', face_img)
                face_image_base64 = base64.b64encode(buffer).decode('utf-8')
                processed_faces.append({
                    "name": name,
                    "embedding": base64.b64encode(face_encoding.tobytes()).decode('utf-8'),
                    "image": face_image_base64,
                    "coordinates": {"top": y1, "right": x2, "bottom": y2, "left": x1}
                })
                
                # Draw rectangle and name on the frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{name} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    end_time = time.time()
    detection_time = end_time - start_time
    return frame, processed_faces, detection_time

def recognize_face(face_encoding, known_face_encodings, known_face_names):
    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
    name = "Unknown"
    if True in matches:
        first_match_index = matches.index(True)
        name = known_face_names[first_match_index]
    return name

def save_face(face_data, user):
    face, created = PermFace.objects.get_or_create(
        name=face_data['name'],
        user=user,
        defaults={'embeddings': face_data['embedding']}
    )
    if created:
        face.image_paths = [face_data['image']]  # Store base64 image
        face.save()
    return face