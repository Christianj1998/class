import os
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image
from loguru import logger
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
from pathlib import Path
import time

@dataclass
class Face:
    bbox: np.ndarray  # [x1, y1, x2, y2]
    kps: np.ndarray   # 5 key points
    det_score: float  # detection score
    embedding: np.ndarray
    age: Optional[int] = None
    gender: Optional[str] = None  # 'Male' or 'Female'
    face_img: Optional[np.ndarray] = None

@dataclass
class KnownFace:
    name: str
    lastname: str
    age: int
    cedula: str
    birth_date: str
    crime: str
    case_number: str
    embedding: np.ndarray
    image_path: str

class FaceDetector:
    def __init__(self, config: dict):
        self.config = config
        self.recognition_threshold = config['recognition']['recognition_threshold']
        self.detection_threshold = config['recognition']['detection_threshold']
        self.max_batch_size = config['recognition']['max_batch_size']
        self.device = config['recognition']['device']
        self.analysis_enabled = config['recognition'].get('analysis_enabled', True)
        self.model = self._load_model()
        self.known_faces: List[KnownFace] = []
        
    def _load_model(self) -> FaceAnalysis:
        """Load Model insightface"""
        try:
            model = FaceAnalysis(
                name='buffalo_l',
                root='./models',
                allowed_modules=['detection', 'recognition', 'genderage']
            )
            model.prepare(
                ctx_id=0 if self.device == 'cuda' else -1,
                det_thresh=self.detection_threshold,
                det_size=(640, 640)
            )
            logger.success("Face detection model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load face detection model: {e}")
            raise

    def load_known_faces(self, known_faces_dir: str) -> None:
        """Load known faces from directory (backward compatibility)"""
        try:
            self.known_faces.clear()
            known_faces_dir = Path(known_faces_dir)
            
            if not known_faces_dir.exists():
                logger.warning(f"Known faces directory {known_faces_dir} does not exist")
                return
                
            for face_file in known_faces_dir.glob('*.*'):
                if face_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                    continue
                    
                try:
                    img = cv2.imread(str(face_file))
                    if img is None:
                        logger.warning(f"Could not read image {face_file}")
                        continue
                        
                    faces = self.model.get(img)
                    if len(faces) == 0:
                        logger.warning(f"No faces found in {face_file}")
                        continue
                        
                    face = faces[0]
                    name = face_file.stem
                    
                    # Parse filename to extract information
                    # Format: cedula_timestamp.jpg
                    parts = name.rsplit('_', 1)
                    cedula = parts[0] if len(parts) > 1 else name
                    
                    self.known_faces.append(KnownFace(
                        name=name,
                        lastname="",
                        age=0,
                        cedula=cedula,
                        birth_date="",
                        crime="",
                        case_number="",
                        embedding=face.embedding,
                        image_path=str(face_file)
                    ))
                    logger.info(f"Loaded known face: {name}")
                    
                except Exception as e:
                    logger.error(f"Error processing {face_file}: {e}")
                    
            logger.info(f"Loaded {len(self.known_faces)} known faces")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            raise

    def load_known_faces_from_db(self, database) -> None:
        """Load known faces from database"""
        try:
            self.known_faces.clear()
            db_faces = database.get_known_faces()
            
            for face_data in db_faces:
                try:
                    embedding = np.frombuffer(face_data['embedding'], dtype=np.float32)
                    
                    self.known_faces.append(KnownFace(
                        name=face_data['name'],
                        lastname=face_data['lastname'],
                        age=face_data['age'],
                        cedula=face_data['cedula'],
                        birth_date=face_data['birth_date'],
                        crime=face_data['crime'],
                        case_number=face_data['case_number'],
                        embedding=embedding,
                        image_path=face_data['image_path']
                    ))
                except Exception as e:
                    logger.error(f"Error processing face data: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.known_faces)} known faces from database")
            
        except Exception as e:
            logger.error(f"Error loading known faces from database: {e}")

    def detect_faces(self, image: np.ndarray) -> List[Face]:
        """Detect faces in an image"""
        try:
            faces = self.model.get(image)
            results = []
            
            for face in faces:
                face_img = self._extract_face_image(image, face.bbox)

                results.append(Face(
                    bbox=face.bbox,
                    kps=face.kps,
                    det_score=face.det_score,
                    embedding=face.embedding,
                    age=self._get_age(face),
                    gender=self._get_gender(face),
                    face_img=face_img
                ))
            return results
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def recognize_faces(self, faces: List[Face]) -> List[Tuple[Face, Optional[KnownFace], float]]:
        """Recognize faces against known faces database"""
        results = []
        
        if not self.known_faces:
            return [(face, None, 0.0) for face in faces]
            
        try:
            known_embeddings = np.array([kf.embedding for kf in self.known_faces])
            
            for face in faces:
                if face.embedding is None or len(face.embedding) == 0:
                    results.append((face, None, 0.0))
                    continue
                    
                similarities = np.dot(known_embeddings, face.embedding) / (
                    np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(face.embedding)
                )
                
                max_idx = np.argmax(similarities)
                max_similarity = similarities[max_idx]
                
                if max_similarity > self.recognition_threshold:
                    results.append((face, self.known_faces[max_idx], max_similarity))
                else:
                    results.append((face, None, max_similarity))
                    
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return [(face, None, 0.0) for face in faces]
            
        return results

    def _extract_face_image(self, image: np.ndarray, bbox: np.ndarray) -> np.ndarray:
        """Extract face region from image"""
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        
        if x1 >= x2 or y1 >= y2:
            return np.array([])
            
        return image[y1:y2, x1:x2].copy()

    def add_known_face(self, image: np.ndarray, name: str, lastname: str,
                      age: int, cedula: str, birth_date: str,
                      crime: str, case_number: str,
                      save_dir: str, database=None, created_by=None) -> bool:
        """Add a new known face to the database"""
        try:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            faces = self.detect_faces(image)
            if not faces:
                logger.warning("No faces found in the provided image")
                return False
                
            face = faces[0]
            timestamp = int(time.time())
            face_path = save_dir / f"{cedula}_{timestamp}.jpg"
            cv2.imwrite(str(face_path), image)
            
            # Save to database if provided
            if database:
                embedding_bytes = face.embedding.tobytes()
                success = database.add_known_face(
                    name, lastname, age, cedula, birth_date,
                    crime, case_number, embedding_bytes,
                    str(face_path), created_by
                )
                if not success:
                    return False
            
            # Add to memory
            self.known_faces.append(KnownFace(
                name=name,
                lastname=lastname,
                age=age,
                cedula=cedula,
                birth_date=birth_date,
                crime=crime,
                case_number=case_number,
                embedding=face.embedding,
                image_path=str(face_path)
            ))
            
            logger.info(f"Added new known face: {name} {lastname} - Cedula: {cedula}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding known face: {e}")
            return False

    def _get_age(self, face) -> Optional[int]:
        """Extract age estimation if available"""
        if not self.analysis_enabled:
            return None
        return int(face.age) if hasattr(face, 'age') else None
    
    def _get_gender(self, face) -> Optional[str]:
        """Extract gender prediction if available"""
        if not self.analysis_enabled:
            return None
        if not hasattr(face, 'sex') or face.sex is None:
            return None
        return 'Female' if np.argmax(face.sex) == 1 else 'Male'
    