#camera/face_recognition_module.py
import numpy as np
import cv2
from mtcnn.mtcnn import MTCNN
import face_recognition
from .models import Face
import time
import base64

# Initialize the MTCNN detector once
detector = MTCNN()

def detect_faces(frame):
    return detector.detect_faces(frame)

def recognize_faces(frame, known_face_encodings, known_face_names):
    rgb_frame = frame[:, :, ::-1]
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    face_names = []
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]
        face_names.append(name)
    
    return face_locations, face_names, face_encodings

def process_frame(frame):
    start_time = time.time()

    # Fetch known faces from the database
    known_faces = Face.objects.all()
    known_face_encodings = [np.frombuffer(face.embedding, dtype=np.float64) for face in known_faces]
    known_face_names = [face.name for face in known_faces]

    # Detect and recognize faces
    face_locations, face_names, face_encodings = recognize_faces(frame, known_face_encodings, known_face_names)

    detected_faces = []

    for (top, right, bottom, left), name, face_encoding in zip(face_locations, face_names, face_encodings):
        if name == "Unknown":
            face_base64 = base64.b64encode(face_encoding.tobytes()).decode('utf-8')
            face_image = frame[top:bottom, left:right]
            _, buffer = cv2.imencode('.jpg', face_image)
            face_image_base64 = base64.b64encode(buffer).decode('utf-8')
            detected_faces.append({
                "name": name,
                "embedding": face_base64,
                "image": face_image_base64,
                "coordinates": {"top": top, "right": right, "bottom": bottom, "left": left}
            })

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    end_time = time.time()
    detection_time = time.strftime('%I:%M %p', time.localtime(end_time))

    return frame, detected_faces, detection_time
