#camera/face_recognition_module.py
import cv2
import numpy as np
from deep_sort_realtime.deep_sort import nn_matching
from deep_sort_realtime.deep_sort.detection import Detection
from deep_sort_realtime.deep_sort.tracker import Tracker
import os
from datetime import datetime, date
import time
import logging
import threading
import queue
import torch
from ultralytics import YOLO
from django.utils import timezone
from django.conf import settings
from .models import TempFace, PermFace

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize YOLO model
device = 'cuda' if torch.cuda.is_available() else 'cpu'
facemodel = YOLO('yolov8m-face.pt').to(device)

# Initialize DeepSORT
max_cosine_distance = 0.3
nn_budget = 300
metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
tracker = Tracker(metric, max_age=100)

# Queues for parallel processing
frame_queue = queue.Queue(maxsize=30)
result_queue = queue.Queue(maxsize=30)

# Flag to signal thread termination
terminate_flag = False

# Global variables for face ID management
current_date = date.today()
face_id_counter = 1
face_id_mapping = {}
frame_save_counter = {}

def detect_faces(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = facemodel(frame_rgb, conf=0.49)
    faces = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            confidence = box.conf.item()
            faces.append([x1, y1, x2 - x1, y2 - y1, confidence])
    return np.array(faces)

def generate_simple_feature(face, frame):
    x, y, w, h, _ = face.astype(int)
    face_roi = frame[y:y+h, x:x+w]
    if face_roi.size == 0:
        return np.zeros(64*64)
    face_roi = cv2.resize(face_roi, (64, 64))
    feature = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY).flatten()
    norm = np.linalg.norm(feature)
    return feature / norm if norm != 0 else feature

def get_next_face_id():
    global face_id_counter, current_date
    today = date.today()
    if today != current_date:
        current_date = today
        face_id_counter = 1
        face_id_mapping.clear()
    face_id = f"unknown_{face_id_counter:03d}"
    face_id_counter += 1
    return face_id

def save_face_image(frame, track, user):
    global face_id_mapping, frame_save_counter
    track_id = int(track.track_id)
    if track_id not in face_id_mapping:
        face_id_mapping[track_id] = f"unknown_{face_id_counter:03d}"
        frame_save_counter[track_id] = 0
    
    frame_save_counter[track_id] += 1
    if frame_save_counter[track_id] % 7 != 0:
        return None
    
    face_id = face_id_mapping[track_id]
    today = current_date.strftime("%Y-%m-%d")
    directory = os.path.join(settings.MEDIA_ROOT, 'faces', today, face_id)
    os.makedirs(directory, exist_ok=True)
    
    bbox = track.to_tlbr()
    h, w = frame.shape[:2]
    pad_w = 0.2 * (bbox[2] - bbox[0])
    pad_h = 0.2 * (bbox[3] - bbox[1])
    x1, y1 = max(0, int(bbox[0] - pad_w)), max(0, int(bbox[1] - pad_h))
    x2, y2 = min(w, int(bbox[2] + pad_w)), min(h, int(bbox[3] + pad_h))
    
    face_img = frame[y1:y2, x1:x2]
    
    if face_img.size > 0:
        image_count = len([f for f in os.listdir(directory) if f.endswith('.jpg')])
        if image_count < 15:
            filename = os.path.join(directory, f"{face_id}_{image_count:02d}.jpg")
            cv2.imwrite(filename, face_img)
            
            # Update database using Django ORM
            temp_face, created = TempFace.objects.get_or_create(user=user, face_id=face_id)
            temp_face.image_paths.append(filename)
            temp_face.save()

            # Check if this face should be moved to PermFace
            if len(temp_face.image_paths) >= 15:
                perm_face = PermFace.objects.create(
                    user=user,
                    name=f"Unknown{PermFace.objects.filter(name__startswith='Unknown', user=user).count() + 1:03d}",
                    image_paths=temp_face.image_paths
                )
                temp_face.delete()
                return perm_face
            return temp_face
    
    return None

def process_frame(frame, user):
    faces = detect_faces(frame)
    detections = [Detection(face[:4], face[4], generate_simple_feature(face, frame)) for face in faces]
    
    tracker.predict()
    tracker.update(detections)
    
    detected_faces = []
    for track in tracker.tracks:
        if not track.is_confirmed() or track.time_since_update > 1:
            continue
        bbox = track.to_tlbr()
        face = save_face_image(frame, track, user)
        if face:
            cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (255, 0, 0), 2)
            cv2.putText(frame, face.name if isinstance(face, PermFace) else "Processing", 
                        (int(bbox[0]), int(bbox[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            detected_faces.append({
                'id': face.id,
                'name': face.name if isinstance(face, PermFace) else "Processing",
                'face_id': face.face_id if isinstance(face, TempFace) else None,
                'time': timezone.localtime(face.timestamp if isinstance(face, TempFace) else face.last_seen).strftime('%I:%M %p')
            })
    
    return frame, detected_faces

def frame_producer(cap):
    while not terminate_flag:
        ret, frame = cap.read()
        if ret:
            if frame_queue.full():
                frame_queue.get()
            frame_queue.put(frame)
        else:
            time.sleep(0.1)

def frame_consumer(user):
    while not terminate_flag:
        if not frame_queue.empty():
            frame = frame_queue.get()
            processed_frame, detected_faces = process_frame(frame, user)
            if result_queue.full():
                result_queue.get()
            result_queue.put((processed_frame, detected_faces))
        else:
            time.sleep(0.01)

def generate_frames(cap, user):
    producer_thread = threading.Thread(target=frame_producer, args=(cap,))
    consumer_thread = threading.Thread(target=frame_consumer, args=(user,))
    producer_thread.start()
    consumer_thread.start()
    
    try:
        while True:
            if not result_queue.empty():
                frame, detected_faces = result_queue.get()
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n', detected_faces)
            else:
                time.sleep(0.01)
    finally:
        global terminate_flag
        terminate_flag = True
        producer_thread.join()
        consumer_thread.join()
        cap.release()