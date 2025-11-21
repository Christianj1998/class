from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QDateEdit, QComboBox, QSpacerItem, QSizePolicy,
                            QSplitter, QFrame, QMessageBox, QDialog)
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtGui import QPixmap
from loguru import logger
import time
from datetime import datetime, timedelta
from typing import List, Optional
import cv2

from core.database import FaceDatabase, FaceLogEntry
from core.utils import numpy_to_pixmap

class HistoryViewer(QWidget):
    def __init__(self, database, config):
        """Initialize the HistoryViewer with database and configuration, set up UI and load initial data."""
        super().__init__()
        self.database = database
        self.config = config
        self.current_entry = None
        
        self.setup_ui()
        self.load_camera_list()
        self.load_face_list()
        
        # Cargar historial después de que todo esté configurado
        logger.info("Initializing HistoryViewer and loading history...")
        self.refresh_history()
        
    def setup_ui(self):
        """Set up all UI components including filters, list view, and detail view for history entries."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)
        
        # Título
        title = QLabel("📊 Historial de Detecciones")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: white;
            margin-bottom: 16px;
        """)
        main_layout.addWidget(title)
        
        # Filter controls en una tarjeta
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(16)
        
        # Date range filters
        date_group = QFrame()
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(8)
        
        date_label = QLabel("📅 Rango de Fechas:")
        date_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        date_layout.addWidget(date_label)
        
        date_range_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setStyleSheet("""
            QDateEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px;
                min-width: 120px;
            }
        """)
        date_range_layout.addWidget(self.start_date)
        
        date_range_layout.addWidget(QLabel("→"))
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setStyleSheet(self.start_date.styleSheet())
        date_range_layout.addWidget(self.end_date)
        
        date_layout.addLayout(date_range_layout)
        filter_layout.addWidget(date_group)
        
        # Camera filter
        camera_group = QFrame()
        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setSpacing(8)
        
        camera_label = QLabel("📹 Cámara:")
        camera_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        camera_layout.addWidget(camera_label)
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Todas las Cámaras", None)
        self.camera_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px;
                min-width: 150px;
            }
        """)
        camera_layout.addWidget(self.camera_combo)
        filter_layout.addWidget(camera_group)
        
        # Face filter
        face_group = QFrame()
        face_layout = QVBoxLayout(face_group)
        face_layout.setSpacing(8)
        
        face_label = QLabel("👤 Persona:")
        face_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        face_layout.addWidget(face_label)
        
        self.face_combo = QComboBox()
        self.face_combo.addItem("Todas las Personas", None)
        self.face_combo.setStyleSheet(self.camera_combo.styleSheet())
        face_layout.addWidget(self.face_combo)
        filter_layout.addWidget(face_group)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Actualizar")
        self.refresh_btn.clicked.connect(self.refresh_history)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 120, 212, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
        """)
        filter_layout.addWidget(self.refresh_btn, 0, Qt.AlignBottom)
        
        filter_layout.addStretch()
        main_layout.addWidget(filter_frame)
        
        # Contador de resultados
        self.count_label = QLabel("Cargando...")
        self.count_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px; margin: 8px 0;")
        main_layout.addWidget(self.count_label)
        
        # Splitter for history list and details
        splitter = QSplitter(Qt.Horizontal)
        
        # History list en una tarjeta
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        list_layout = QVBoxLayout(list_frame)
        
        list_title = QLabel("📋 Registros")
        list_title.setStyleSheet("color: white; font-weight: 600; font-size: 14px; margin-bottom: 8px;")
        list_layout.addWidget(list_title)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 12px;
                border-radius: 6px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.3);
                border: 1px solid rgba(0, 120, 212, 0.5);
            }
        """)
        self.history_list.currentItemChanged.connect(self.on_history_item_selected)
        list_layout.addWidget(self.history_list)
        
        splitter.addWidget(list_frame)
        
        # Details panel
        details_frame = QFrame()
        details_frame.setStyleSheet(list_frame.styleSheet())
        details_layout = QVBoxLayout(details_frame)
        
        details_title = QLabel("🔍 Detalles")
        details_title.setStyleSheet("color: white; font-weight: 600; font-size: 14px; margin-bottom: 8px;")
        details_layout.addWidget(details_title)
        
        # Image display
        self.image_label = QLabel("Selecciona un registro para ver detalles")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 20px;
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        details_layout.addWidget(self.image_label)
        
        # Details text
        self.details_label = QLabel()
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        details_layout.addWidget(self.details_label)
        
        # Screenshot button
        self.view_screenshot_btn = QPushButton("📷 Ver Captura Completa")
        self.view_screenshot_btn.clicked.connect(self.view_screenshot)
        self.view_screenshot_btn.setEnabled(False)
        self.view_screenshot_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 167, 69, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(40, 167, 69, 1);
            }
            QPushButton:disabled {
                background-color: rgba(40, 167, 69, 0.3);
                color: rgba(255, 255, 255, 0.4);
            }
        """)
        details_layout.addWidget(self.view_screenshot_btn)
        
        splitter.addWidget(details_frame)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
        
    def load_camera_list(self):
        """Load the list of available cameras from the configuration file into the camera filter dropdown."""
        try:
            with open('config/camera_config.yaml', 'r') as f:
                import yaml
                config = yaml.safe_load(f)
                
            for camera in config.get('cameras', []):
                self.camera_combo.addItem(
                    f"Cámara {camera['id']}: {camera.get('name', '')}",
                    camera['id']
                )
            logger.info(f"Loaded {self.camera_combo.count() - 1} cameras into filter")
                
        except Exception as e:
            logger.error(f"Error loading camera config: {e}")
            
    def load_face_list(self):
        """Load the list of known faces from the database into the face filter dropdown."""
        try:
            known_faces = self.database.get_known_faces()
            for face in known_faces:
                self.face_combo.addItem(face['name'], face['name'])
            logger.info(f"Loaded {len(known_faces)} known faces into filter")
                
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")

    def refresh_history(self):
        """Fetch and display filtered history entries from the database in the history list."""
        try:
            logger.info("Refreshing history...")
            
            # Get filter values
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate() + timedelta(days=1)  # Include entire end day
            
            start_timestamp = datetime.combine(start_date, datetime.min.time()).timestamp()
            end_timestamp = datetime.combine(end_date, datetime.min.time()).timestamp()
            
            camera_id = self.camera_combo.currentData()
            face_name = self.face_combo.currentData()
            
            logger.info(f"Filters - Start: {start_date}, End: {end_date}, Camera: {camera_id}, Face: {face_name}")
            
            # Get filtered history
            entries = self.database.get_face_logs(
                limit=1000,
                camera_id=camera_id,
                face_name=face_name,
                start_time=start_timestamp,
                end_time=end_timestamp
            )
            
            logger.info(f"Retrieved {len(entries)} entries from database")
            
            # Populate list
            self.history_list.clear()
            
            if not entries:
                self.count_label.setText("❌ No se encontraron registros con los filtros seleccionados")
                self.history_list.addItem("No hay registros para mostrar")
                return
            
            for entry in entries:
                try:
                    # Convertir timestamp a datetime de manera segura
                    if isinstance(entry.timestamp, (bytes, str)):
                        timestamp = float(entry.timestamp)
                    else:
                        timestamp = entry.timestamp
                    
                    time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Formato mejorado del item
                    confidence_pct = entry.confidence * 100 if entry.confidence <= 1 else entry.confidence
                    item_text = f"🕒 {time_str} | 👤 {entry.face_name} | 📹 {entry.camera_name} | 🎯 {confidence_pct:.1f}%"
                    
                    item = self.history_list.addItem(item_text)
                    self.history_list.item(self.history_list.count() - 1).setData(Qt.UserRole, entry)
                    
                except Exception as e:
                    logger.error(f"Error processing history entry: {e}")
                    logger.error(f"Entry data: {entry}")
                    continue
            
            self.count_label.setText(f"✅ Se encontraron {len(entries)} registro(s)")
            logger.info(f"Successfully loaded {len(entries)} entries into list")
                    
        except Exception as e:
            logger.error(f"Error refreshing history: {e}", exc_info=True)
            self.count_label.setText(f"❌ Error al cargar historial: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el historial:\n\n{str(e)}\n\nRevisa los logs para más detalles."
            )

    def on_history_item_selected(self, current, previous):
        """Handle display of detailed information when a history list item is selected."""
        try:
            if current is None:
                self.current_entry = None
                self.image_label.clear()
                self.image_label.setText("Selecciona un registro para ver detalles")
                self.details_label.clear()
                self.view_screenshot_btn.setEnabled(False)
                return
                
            entry = current.data(Qt.UserRole)
            if not isinstance(entry, FaceLogEntry):
                logger.warning(f"Invalid entry type: {type(entry)}")
                return
                
            self.current_entry = entry
            
            # Safely format the timestamp
            try:
                timestamp = float(entry.timestamp) if isinstance(entry.timestamp, (bytes, str)) else entry.timestamp
                time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError) as e:
                logger.warning(f"Invalid timestamp format: {entry.timestamp}")
                time_str = "Hora desconocida"
            
            # Safely format confidence
            try:
                confidence = float(entry.confidence)
                confidence_pct = confidence * 100 if confidence <= 1 else confidence
                confidence_str = f"{confidence_pct:.1f}%"
            except (TypeError, ValueError):
                confidence_str = "N/A"
            
            # Display details with better formatting
            details_text = f"""
            <div style='line-height: 1.8;'>
                <p><b>🕒 Fecha y Hora:</b> {time_str}</p>
                <p><b>📹 Cámara:</b> {entry.camera_name} (ID: {entry.camera_id})</p>
                <p><b>👤 Persona:</b> {entry.face_name}</p>
                <p><b>🎯 Confianza:</b> {confidence_str}</p>
                <p><b>👶 Edad Estimada:</b> {entry.age if entry.age else 'No disponible'}</p>
                <p><b>🚻 Género:</b> {entry.gender if entry.gender else 'No disponible'}</p>
            </div>
            """
            self.details_label.setText(details_text)
            
            # Load and display thumbnail if screenshot exists
            if entry.screenshot_path and len(str(entry.screenshot_path)) > 0:
                screenshot_path = Path(entry.screenshot_path)
                if screenshot_path.exists():
                    try:
                        image = cv2.imread(str(screenshot_path))
                        if image is not None:
                            pixmap = numpy_to_pixmap(image)
                            scaled_pixmap = pixmap.scaled(
                                self.image_label.width() - 40,
                                self.image_label.height() - 40,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation
                            )
                            self.image_label.setPixmap(scaled_pixmap)
                            self.image_label.setStyleSheet("""
                                QLabel {
                                    background-color: rgba(0, 0, 0, 0.3);
                                    border-radius: 8px;
                                }
                            """)
                            self.view_screenshot_btn.setEnabled(True)
                        else:
                            raise ValueError("Could not load image")
                    except Exception as e:
                        logger.error(f"Error loading thumbnail: {e}")
                        self.image_label.setText("❌ Error al cargar imagen")
                        self.view_screenshot_btn.setEnabled(False)
                else:
                    self.image_label.setText("📷 Captura no encontrada")
                    self.view_screenshot_btn.setEnabled(False)
            else:
                self.image_label.setText("📷 Sin captura disponible")
                self.view_screenshot_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Error displaying history item: {e}", exc_info=True)
            self.details_label.setText(f"<p style='color: #ff6b6b;'>Error al cargar detalles: {str(e)}</p>")
            self.view_screenshot_btn.setEnabled(False)

    def view_screenshot(self):
        """Open a dialog to display the screenshot associated with the selected history entry."""
        if self.current_entry is None or not self.current_entry.screenshot_path:
            QMessageBox.information(self, "Sin Captura", "No hay captura disponible para este registro")
            return
            
        try:
            # Check if file exists
            screenshot_path = Path(self.current_entry.screenshot_path)
            if not screenshot_path.exists():
                QMessageBox.warning(self, "Archivo No Encontrado", f"No se encontró la captura: {screenshot_path}")
                return
                
            image = cv2.imread(str(screenshot_path))
            if image is None:
                raise ValueError("No se pudo leer la captura")
                
            pixmap = numpy_to_pixmap(image)
            
            # Create a dialog to show the screenshot
            dialog = QDialog(self)
            dialog.setWindowTitle("Captura Completa")
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1a1a2e;
                }
                QLabel {
                    background-color: rgba(0, 0, 0, 0.5);
                    border-radius: 8px;
                }
            """)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setPixmap(pixmap.scaled(
                1000, 750, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(image_label)
            
            close_btn = QPushButton("Cerrar")
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 120, 212, 0.8);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 120, 212, 1);
                }
            """)
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.resize(1050, 850)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error viewing screenshot: {e}")
            QMessageBox.critical(self, "Error", f"No se pudo cargar la captura:\n\n{str(e)}")