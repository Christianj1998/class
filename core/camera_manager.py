import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import time
import threading
import queue
import yaml
from pathlib import Path

@dataclass
class CameraConfig:
    id: int
    name: str
    source: str
    enabled: bool
    width: int
    height: int
    fps: int
    rotate: int

class CameraManager:
    def __init__(self, config_path: str):
        self.cameras: Dict[int, CameraConfig] = {}
        self.capture_threads: Dict[int, threading.Thread] = {}
        self.capture_objects: Dict[int, cv2.VideoCapture] = {}
        self.stop_events: Dict[int, threading.Event] = {}
        self.frame_queues: Dict[int, queue.Queue] = {}
        self.thread_lock = threading.Lock()
        self.load_config(config_path)

    def _cleanup_camera_thread(self, cam_id: int, timeout: float = 5.0):
        """Clean up camera thread resources with improved timeout handling"""
        try:
            with self.thread_lock:
                # Signal thread to stop
                if cam_id in self.stop_events:
                    self.stop_events[cam_id].set()
                
                # Wait for thread to finish with timeout
                if cam_id in self.capture_threads:
                    thread = self.capture_threads[cam_id]
                    if thread.is_alive():
                        logger.debug(f"Waiting for camera {cam_id} thread to stop...")
                        thread.join(timeout=timeout)
                        
                        if thread.is_alive():
                            logger.error(f"Camera {cam_id} thread did not stop within {timeout}s timeout")
                            # Thread is still alive but we'll proceed with cleanup
                        else:
                            logger.debug(f"Camera {cam_id} thread stopped successfully")
                    
                    del self.capture_threads[cam_id]
                
                # Close video capture object
                if cam_id in self.capture_objects:
                    try:
                        cap = self.capture_objects[cam_id]
                        if cap.isOpened():
                            cap.release()
                        del self.capture_objects[cam_id]
                        logger.debug(f"Released video capture for camera {cam_id}")
                    except Exception as e:
                        logger.error(f"Error releasing video capture for camera {cam_id}: {e}")
                
                # Clean up queue
                if cam_id in self.frame_queues:
                    try:
                        # Empty the queue
                        while not self.frame_queues[cam_id].empty():
                            try:
                                self.frame_queues[cam_id].get_nowait()
                            except queue.Empty:
                                break
                        del self.frame_queues[cam_id]
                    except Exception as e:
                        logger.error(f"Error cleaning queue for camera {cam_id}: {e}")
                
                # Clean up stop event
                if cam_id in self.stop_events:
                    del self.stop_events[cam_id]
                    
                logger.info(f"Cleaned up resources for camera {cam_id}")
                
        except Exception as e:
            logger.error(f"Error during cleanup of camera {cam_id}: {e}")

    def load_config(self, config_path: str) -> None:
        """Load camera configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            self.cameras.clear()
            for cam_config in config.get('cameras', []):
                cam_id = cam_config['id']
                self.cameras[cam_id] = CameraConfig(
                    id=cam_id,
                    name=cam_config.get('name', f'Camera {cam_id}'),
                    source=cam_config['source'],
                    enabled=cam_config.get('enabled', True),
                    width=cam_config['resolution']['width'],
                    height=cam_config['resolution']['height'],
                    fps=cam_config.get('fps', 30),
                    rotate=cam_config.get('rotate', 0)
                )
                
            logger.info(f"Loaded {len(self.cameras)} camera configurations")
            
        except Exception as e:
            logger.error(f"Error loading camera config: {e}")
            raise

    def _validate_camera_source(self, cam_id: int, source) -> bool:
        """Validate camera source before attempting to connect"""
        try:
            # For HTTP/RTSP sources
            if isinstance(source, str) and (source.startswith('http') or source.startswith('rtsp')):
                logger.info(f"Validating network camera {cam_id}: {source}")
                
                # Try a quick connection test
                import requests
                from urllib.parse import urlparse
                
                try:
                    # Extract base URL for ping test
                    parsed = urlparse(source)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    # Quick HEAD request with short timeout
                    response = requests.head(base_url, timeout=3)
                    if response.status_code >= 400:
                        logger.warning(f"Camera {cam_id} returned status {response.status_code}")
                        return False
                    
                    logger.info(f"Network camera {cam_id} is reachable")
                    return True
                    
                except requests.RequestException as e:
                    logger.warning(f"Camera {cam_id} validation failed: {e}")
                    return False
            
            # For local cameras (integer index)
            elif isinstance(source, int):
                logger.info(f"Local camera index {source} detected")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating camera {cam_id} source: {e}")
            return False

    def start_all_cameras(self) -> None:
        """Start all enabled cameras"""
        for cam_id, cam_config in self.cameras.items():
            if cam_config.enabled:
                self.start_camera(cam_id)

    def stop_all_cameras(self) -> None:
        """Stop all camera threads"""
        with self.thread_lock:
            cam_ids = list(self.capture_threads.keys())
        
        for cam_id in cam_ids:
            self.stop_camera(cam_id)
        
        logger.info("All camera threads stopped")

    def start_camera(self, cam_id: int) -> bool:
        """Start a single camera with validation"""
        if cam_id not in self.cameras:
            logger.error(f"Camera ID {cam_id} not found in configuration")
            return False
            
        cam_config = self.cameras[cam_id]
        
        if not cam_config.enabled:
            logger.warning(f"Camera ID {cam_id} is disabled in configuration")
            return False
        
        # Validate source before starting
        if not self._validate_camera_source(cam_id, cam_config.source):
            logger.error(f"Camera ID {cam_id} source validation failed")
            return False
        
        # Clean up any existing thread first
        if cam_id in self.capture_threads:
            logger.info(f"Stopping existing thread for camera {cam_id}")
            self._cleanup_camera_thread(cam_id)
        
        try:
            # Create new resources
            self.frame_queues[cam_id] = queue.Queue(maxsize=2)
            self.stop_events[cam_id] = threading.Event()
            
            # Create and start thread
            thread = threading.Thread(
                target=self._capture_frames,
                args=(cam_id,),
                daemon=True,
                name=f"CameraThread-{cam_id}"
            )
            
            with self.thread_lock:
                self.capture_threads[cam_id] = thread
            
            thread.start()
            logger.info(f"Started camera ID {cam_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera {cam_id}: {e}")
            self._cleanup_camera_thread(cam_id)
            return False

    def stop_camera(self, cam_id: int) -> bool:
        """Stop a single camera"""
        if cam_id in self.capture_threads:
            self._cleanup_camera_thread(cam_id, timeout=5.0)
            logger.info(f"Stopped camera ID {cam_id}")
            return True
        return False

    def _capture_frames(self, cam_id: int) -> None:
        """Thread function to capture frames from a camera"""
        cam_config = self.cameras[cam_id]
        cap = None
        retry_count = 0
        max_retries = 3
        retry_delay = 2.0
        
        try:
            # Handle different source types
            source = int(cam_config.source) if str(cam_config.source).isdigit() else cam_config.source
            
            # Try to open camera with retries
            while retry_count < max_retries and not self.stop_events[cam_id].is_set():
                try:
                    cap = cv2.VideoCapture(source)
                    
                    if not cap.isOpened():
                        raise RuntimeError(f"Failed to open camera source: {source}")
                    
                    # Store capture object for cleanup
                    with self.thread_lock:
                        self.capture_objects[cam_id] = cap
                    
                    # Set camera properties
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_config.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_config.height)
                    cap.set(cv2.CAP_PROP_FPS, cam_config.fps)
                    
                    # Additional settings for better performance
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffering
                    
                    logger.info(f"Camera ID {cam_id} opened successfully")
                    break
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Camera {cam_id} open attempt {retry_count} failed: {e}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to open camera ID {cam_id} after {max_retries} attempts")
                        return
            
            if cap is None or not cap.isOpened():
                logger.error(f"Failed to open camera ID {cam_id} with source {cam_config.source}")
                return
            
            # Frame capture loop
            consecutive_failures = 0
            max_consecutive_failures = 10
            
            while not self.stop_events[cam_id].is_set():
                try:
                    ret, frame = cap.read()
                    
                    if not ret or frame is None:
                        consecutive_failures += 1
                        logger.warning(f"Camera ID {cam_id} read failed (attempt {consecutive_failures}/{max_consecutive_failures})")
                        
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"Camera ID {cam_id} exceeded maximum consecutive failures")
                            break
                        
                        time.sleep(0.5)
                        continue
                    
                    # Reset failure counter on success
                    consecutive_failures = 0
                    
                    # Apply rotation if needed
                    if cam_config.rotate == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif cam_config.rotate == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif cam_config.rotate == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    
                    # Put frame in queue (non-blocking)
                    if cam_id in self.frame_queues:
                        # Remove old frame if queue is full
                        if self.frame_queues[cam_id].full():
                            try:
                                self.frame_queues[cam_id].get_nowait()
                            except queue.Empty:
                                pass
                        
                        try:
                            self.frame_queues[cam_id].put(frame, block=False)
                        except queue.Full:
                            pass  # Frame dropped, continue to next
                    
                    # Small delay to prevent CPU overload
                    time.sleep(0.001)
                    
                except Exception as e:
                    logger.error(f"Error in camera ID {cam_id} capture loop: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        break
                    time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Fatal error in camera ID {cam_id} capture thread: {e}")
            
        finally:
            # Cleanup
            if cap is not None:
                try:
                    cap.release()
                    logger.debug(f"Released VideoCapture for camera {cam_id}")
                except Exception as e:
                    logger.error(f"Error releasing VideoCapture for camera {cam_id}: {e}")
            
            logger.info(f"Camera ID {cam_id} capture thread exiting")

    def get_frame(self, cam_id: int) -> Optional[np.ndarray]:
        """Get the latest frame from a camera"""
        if cam_id not in self.frame_queues:
            return None
            
        try:
            return self.frame_queues[cam_id].get_nowait()
        except queue.Empty:
            return None

    def get_all_frames(self) -> Dict[int, np.ndarray]:
        """Get latest frames from all cameras"""
        frames = {}
        for cam_id in list(self.frame_queues.keys()):
            frame = self.get_frame(cam_id)
            if frame is not None:
                frames[cam_id] = frame
        return frames

    def get_camera_status(self, cam_id: int) -> Dict:
        """Get camera status information"""
        if cam_id not in self.cameras:
            return {}
        
        with self.thread_lock:
            is_running = cam_id in self.capture_threads and self.capture_threads[cam_id].is_alive()
            
        status = {
            'id': cam_id,
            'name': self.cameras[cam_id].name,
            'running': is_running,
            'frame_queue_size': self.frame_queues[cam_id].qsize() if cam_id in self.frame_queues else 0,
            'enabled': self.cameras[cam_id].enabled,
            'source': self.cameras[cam_id].source
        }
        return status

    def get_all_camera_status(self) -> List[Dict]:
        """Get status for all cameras"""
        return [self.get_camera_status(cam_id) for cam_id in self.cameras]

    def __del__(self):
        """Destructor to ensure all cameras are stopped"""
        try:
            self.stop_all_cameras()
        except Exception as e:
            logger.error(f"Error in CameraManager destructor: {e}")