# camera/face_recognition_module.py

import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deep_sort import nn_matching
from deep_sort_realtime.deep_sort.detection import Detection
from deep_sort_realtime.deep_sort.tracker import Tracker
import asyncio
import logging
from asgiref.sync import sync_to_async
from .models import TempFace, PermFace
from django.conf import settings
import os

logger = logging.getLogger(__name__)

class FaceRecognitionProcessor:
    def __init__(self):
        # Initialize YOLO model
        model_path = os.path.join(settings.BASE_DIR, 'yolov8m-face.pt')
        self.facemodel = YOLO(model_path)
        logger.info(f"YOLO model loaded from: {model_path}")

        # Initialize DeepSORT
        max_cosine_distance = 0.3
        nn_budget = 300
        metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
        self.tracker = Tracker(metric, max_age=100)

        # Initialize face ID management
        self.face_id_counter = 1
        self.face_id_mapping = {}

    async def process_frame(self, frame):
        # Detect faces
        faces = await self.detect_faces(frame)

        # Generate features and create detections
        detections = [Detection(face[:4], face[4], self.generate_simple_feature(face, frame)) for face in faces]

        # Update tracker
        self.tracker.predict()
        self.tracker.update(detections)

        detected_faces = []
        for track in self.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue

            bbox = track.to_tlbr()
            face, image_url = await self.save_face_image(frame, track)
            if face:
                # Draw bounding box and label on the frame
                cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (255, 0, 0), 2)
                cv2.putText(frame, face.name if isinstance(face, PermFace) else "Processing", 
                            (int(bbox[0]), int(bbox[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Append face information to detected_faces list
                detected_faces.append({
                    'id': face.id,
                    'name': face.name if isinstance(face, PermFace) else "Processing",
                    'face_id': face.face_id if isinstance(face, TempFace) else None,
                    'image_url': image_url
                })

        return frame, detected_faces

    @sync_to_async
    def detect_faces(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.facemodel(frame_rgb, conf=0.5)
        faces = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = box.conf.item()
                faces.append([x1, y1, x2 - x1, y2 - y1, confidence])
        return np.array(faces)

    def generate_simple_feature(self, face, frame):
        x, y, w, h, _ = face.astype(int)
        face_roi = frame[y:y+h, x:x+w]
        if face_roi.size == 0:
            return np.zeros(64*64)
        face_roi = cv2.resize(face_roi, (64, 64))
        feature = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY).flatten()
        norm = np.linalg.norm(feature)
        return feature / norm if norm != 0 else feature

    @sync_to_async
    def save_face_image(self, frame, track):
        track_id = int(track.track_id)
        if track_id not in self.face_id_mapping:
            self.face_id_mapping[track_id] = f"unknown_{self.face_id_counter:03d}"
            self.face_id_counter += 1

        face_id = self.face_id_mapping[track_id]
        bbox = track.to_tlbr()
        
        # Extract face image
        h, w = frame.shape[:2]
        x1, y1 = max(0, int(bbox[0])), max(0, int(bbox[1]))
        x2, y2 = min(w, int(bbox[2])), min(h, int(bbox[3]))
        face_img = frame[y1:y2, x1:x2]

        if face_img.size > 0:
            # Save face image
            today = datetime.now().strftime("%Y-%m-%d")
            directory = os.path.join(settings.MEDIA_ROOT, 'faces', today, face_id)
            os.makedirs(directory, exist_ok=True)
            image_count = len([f for f in os.listdir(directory) if f.endswith('.jpg')])
            filename = os.path.join(directory, f"{face_id}_{image_count:02d}.jpg")
            cv2.imwrite(filename, face_img)

            # Get the relative path for the URL
            relative_path = os.path.relpath(filename, settings.MEDIA_ROOT)
            image_url = f"{settings.MEDIA_URL}{relative_path}"

            # Update database
            temp_face, created = TempFace.objects.get_or_create(face_id=face_id)
            temp_face.image_paths.append(image_url)
            temp_face.save()

            # Check if this face should be moved to PermFace
            if len(temp_face.image_paths) >= 15:
                perm_face = PermFace.objects.create(
                    name=f"Unknown{PermFace.objects.filter(name__startswith='Unknown').count() + 1:03d}",
                    image_paths=temp_face.image_paths
                )
                temp_face.delete()
                return perm_face, image_url

            return temp_face, image_url

        return None, None