import cv2
import numpy as np
from deep_sort_realtime.deep_sort import nn_matching
from deep_sort_realtime.deep_sort.detection import Detection
from deep_sort_realtime.deep_sort.tracker import Tracker
import os
from datetime import datetime, date
import logging
import torch
from ultralytics import YOLO
from django.utils import timezone
from django.conf import settings
from .models import TempFace, PermFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_path = os.path.join(settings.BASE_DIR, 'yolov8m-face.pt')
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")
facemodel = YOLO(model_path).to(device)
logger.info(f"YOLO model loaded on device: {device}")

max_cosine_distance = 0.3
nn_budget = 300
metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
tracker = Tracker(metric, max_age=100)

def detect_faces(frame):
    try:
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
    except Exception as e:
        logger.error(f"Error detecting faces: {str(e)}")
        return np.array([])

def generate_simple_feature(face, frame):
    try:
        x, y, w, h, _ = face.astype(int)
        face_roi = frame[y:y+h, x:x+w]
        if face_roi.size == 0:
            return np.zeros(64*64)
        face_roi = cv2.resize(face_roi, (64, 64))
        feature = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY).flatten()
        norm = np.linalg.norm(feature)
        return feature / norm if norm != 0 else feature
    except Exception as e:
        logger.error(f"Error generating feature: {str(e)}")
        return np.zeros(64*64)

def process_frame(frame, user):
    try:
        logger.info("Processing frame")
        faces = detect_faces(frame)
        logger.info(f"Detected {len(faces)} faces")
        detections = [Detection(face[:4], face[4], generate_simple_feature(face, frame)) for face in faces]
        
        tracker.predict()
        tracker.update(detections)
        
        detected_faces = []
        for track in tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            bbox = track.to_tlbr()
            face, image_url = save_face_image(frame, track, user)
            if face:
                cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (255, 0, 0), 2)
                cv2.putText(frame, face.name if isinstance(face, PermFace) else "Processing", 
                            (int(bbox[0]), int(bbox[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                detected_faces.append({
                    'id': face.id,
                    'name': face.name if isinstance(face, PermFace) else "Processing",
                    'face_id': face.face_id if isinstance(face, TempFace) else None,
                    'time': timezone.localtime(face.timestamp if isinstance(face, TempFace) else face.last_seen).strftime('%I:%M %p'),
                    'image_url': image_url
                })
        
        return frame, detected_faces
    except Exception as e:
        logger.error(f"Error processing frame: {str(e)}")
        return frame, []
