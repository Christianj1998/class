import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QFileDialog, QMessageBox, QLineEdit, QComboBox, 
                            QFrame, QSplitter, QListWidgetItem, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont, QColor, QIcon
from loguru import logger
import cv2
import numpy as np
from pathlib import Path

from core.utils import numpy_to_pixmap, resize_image

class FaceManagerDialog(QDialog):
    def __init__(self, face_detector, known_faces_dir):
        super().__init__()
        self.face_detector = face_detector
        self.known_faces_dir = known_faces_dir
        self.current_image = None
        
        self.setWindowTitle("Administrador de Rostros")
        self.setGeometry(150, 100, 1100, 700)
        self.setMinimumSize(900, 600)
        
        self.setup_style()
        self.init_ui()
        self.load_face_list()
        
    def setup_style(self):
        """Aplicar estilo Windows 11"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16213e);
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
            QListWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 10px;
                margin: 3px 0;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.3);
                border: 1px solid rgba(0, 120, 212, 0.5);
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(0, 120, 212, 0.8);
            }
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
            QPushButton:pressed {
                background-color: rgba(0, 100, 180, 1);
            }
            QPushButton#deleteButton {
                background-color: rgba(220, 53, 69, 0.8);
            }
            QPushButton#deleteButton:hover {
                background-color: rgba(220, 53, 69, 1);
            }
            QPushButton#importButton {
                background-color: rgba(40, 167, 69, 0.8);
            }
            QPushButton#importButton:hover {
                background-color: rgba(40, 167, 69, 1);
            }
            QFrame#previewFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border: 2px dashed rgba(255, 255, 255, 0.2);
                border-radius: 12px;
            }
            QFrame#sidePanel {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 8px;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(header)
        
        title = QLabel("Administrador de Rostros")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Gestiona los rostros conocidos del sistema de reconocimiento")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Lista de rostros
        left_panel = QFrame()
        left_panel.setObjectName("sidePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)
        
        list_header = QLabel("Rostros Registrados")
        list_header.setStyleSheet("font-size: 14px; font-weight: 600; color: white;")
        left_layout.addWidget(list_header)
        
        # Contador de rostros
        self.face_count_label = QLabel()
        self.face_count_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
        left_layout.addWidget(self.face_count_label)
        
        self.face_list = QListWidget()
        self.face_list.currentItemChanged.connect(self.on_face_selected)
        left_layout.addWidget(self.face_list)
        
        splitter.addWidget(left_panel)
        
        # Panel derecho - Vista previa y controles
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(16)
        
        # Vista previa
        preview_label = QLabel("Vista Previa")
        preview_label.setStyleSheet("font-size: 14px; font-weight: 600; color: white;")
        right_layout.addWidget(preview_label)
        
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame_layout = QVBoxLayout(preview_frame)
        preview_frame_layout.setContentsMargins(20, 20, 20, 20)
        
        self.face_preview = QLabel()
        self.face_preview.setAlignment(Qt.AlignCenter)
        self.face_preview.setMinimumSize(400, 400)
        self.face_preview.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        # Placeholder cuando no hay imagen
        placeholder_text = "Selecciona un rostro o importa una imagen"
        self.face_preview.setText(placeholder_text)
        self.face_preview.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 14px;
            }
        """)
        
        preview_frame_layout.addWidget(self.face_preview)
        right_layout.addWidget(preview_frame)
        
        # Información del rostro
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        name_label = QLabel("Nombre del Rostro:")
        name_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ingresa el nombre de la persona...")
        info_layout.addWidget(self.name_input)
        
        right_layout.addWidget(info_frame)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.import_btn = QPushButton("Importar Imagen")
        self.import_btn.setObjectName("importButton")
        self.import_btn.clicked.connect(self.import_image)
        button_layout.addWidget(self.import_btn)
        
        self.add_btn = QPushButton("Agregar Rostro")
        self.add_btn.clicked.connect(self.add_face)
        button_layout.addWidget(self.add_btn)
        
        right_layout.addLayout(button_layout)
        
        button_layout2 = QHBoxLayout()
        button_layout2.setSpacing(10)
        
        self.update_btn = QPushButton("Actualizar")
        self.update_btn.clicked.connect(self.update_face)
        button_layout2.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.setObjectName("deleteButton")
        self.delete_btn.clicked.connect(self.delete_face)
        button_layout2.addWidget(self.delete_btn)
        
        right_layout.addLayout(button_layout2)
        
        splitter.addWidget(right_panel)
        
        # Proporciones del splitter
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # Botón cerrar
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setMinimumWidth(150)
        close_layout.addWidget(self.close_btn)
        
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
        
    def load_face_list(self):
        """Cargar lista de rostros"""
        self.face_list.clear()
        known_faces_dir = Path(self.known_faces_dir)
        
        if not known_faces_dir.exists():
            logger.warning(f"Known faces directory {known_faces_dir} does not exist")
            self.face_count_label.setText("0 rostros registrados")
            return
        
        faces = []
        for face_file in known_faces_dir.glob('*.*'):
            if face_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                faces.append(face_file.stem)
        
        # Ordenar alfabéticamente
        faces.sort()
        
        for face_name in faces:
            item = QListWidgetItem(face_name)
            self.face_list.addItem(item)
        
        # Actualizar contador
        count = len(faces)
        self.face_count_label.setText(f"{count} rostro{'s' if count != 1 else ''} registrado{'s' if count != 1 else ''}")
        
    def on_face_selected(self, current, previous):
        """Manejar selección de rostro"""
        if current is None:
            self.face_preview.clear()
            self.face_preview.setText("Selecciona un rostro o importa una imagen")
            self.name_input.clear()
            return
        
        face_name = current.text()
        self.name_input.setText(face_name)
        
        # Cargar y mostrar imagen
        face_path = Path(self.known_faces_dir) / f"{face_name}{self.get_face_extension(face_name)}"
        if not face_path.exists():
            self.show_message("Error", f"Archivo de imagen no encontrado: {face_path}", QMessageBox.Warning)
            return
        
        try:
            image = cv2.imread(str(face_path))
            if image is None:
                raise ValueError("No se pudo leer la imagen")
            
            self.current_image = image
            pixmap = numpy_to_pixmap(image)
            
            # Escalar manteniendo aspecto
            scaled_pixmap = pixmap.scaled(
                self.face_preview.width() - 40,
                self.face_preview.height() - 40,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.face_preview.setPixmap(scaled_pixmap)
            self.face_preview.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 0.2);
                    border-radius: 8px;
                }
            """)
            
        except Exception as e:
            self.show_message("Error", f"Error al cargar imagen: {str(e)}", QMessageBox.Critical)
            logger.error(f"Error loading face image: {e}")
    
    def get_face_extension(self, face_name: str) -> str:
        """Obtener extensión del archivo"""
        known_faces_dir = Path(self.known_faces_dir)
        for ext in ['.jpg', '.jpeg', '.png']:
            if (known_faces_dir / f"{face_name}{ext}").exists():
                return ext
        return ''
    
    def add_face(self):
        """Agregar nuevo rostro"""
        name = self.name_input.text().strip()
        if not name:
            self.show_message("Error", "Por favor ingresa un nombre para el rostro", QMessageBox.Warning)
            return
        
        if self.current_image is None:
            self.show_message("Error", "Por favor importa o selecciona una imagen primero", QMessageBox.Warning)
            return
        
        # Verificar si ya existe
        existing_files = list(Path(self.known_faces_dir).glob(f"{name}.*"))
        if existing_files:
            self.show_message("Error", f"Ya existe un rostro con el nombre '{name}'", QMessageBox.Warning)
            return
        
        # Agregar el rostro
        success = self.face_detector.add_known_face(
            self.current_image, name, self.known_faces_dir)
        
        if success:
            self.show_message("Éxito", f"Rostro '{name}' agregado correctamente", QMessageBox.Information)
            self.load_face_list()
            self.name_input.clear()
            self.face_preview.clear()
            self.face_preview.setText("Selecciona un rostro o importa una imagen")
            self.current_image = None
        else:
            self.show_message("Error", "No se pudo agregar el rostro", QMessageBox.Critical)
    
    def update_face(self):
        """Actualizar rostro existente"""
        current_item = self.face_list.currentItem()
        if current_item is None:
            self.show_message("Error", "Por favor selecciona un rostro para actualizar", QMessageBox.Warning)
            return
        
        old_name = current_item.text()
        new_name = self.name_input.text().strip()
        
        if not new_name:
            self.show_message("Error", "Por favor ingresa un nombre para el rostro", QMessageBox.Warning)
            return
        
        if self.current_image is None:
            self.show_message("Error", "Por favor importa o selecciona una imagen primero", QMessageBox.Warning)
            return
        
        # Renombrar si cambió el nombre
        if old_name != new_name:
            old_path = Path(self.known_faces_dir) / f"{old_name}{self.get_face_extension(old_name)}"
            new_path = Path(self.known_faces_dir) / f"{new_name}{old_path.suffix}"
            
            if new_path.exists():
                self.show_message("Error", f"Ya existe un rostro con el nombre '{new_name}'", QMessageBox.Warning)
                return
            
            try:
                old_path.rename(new_path)
            except Exception as e:
                self.show_message("Error", f"Error al renombrar: {str(e)}", QMessageBox.Critical)
                return
        
        # Actualizar imagen
        try:
            current_path = Path(self.known_faces_dir) / f"{new_name}{self.get_face_extension(new_name)}"
            cv2.imwrite(str(current_path), self.current_image)
            
            # Recargar rostros en el detector
            self.face_detector.load_known_faces(self.known_faces_dir)
            
            self.show_message("Éxito", "Rostro actualizado correctamente", QMessageBox.Information)
            self.load_face_list()
        except Exception as e:
            self.show_message("Error", f"Error al actualizar: {str(e)}", QMessageBox.Critical)
    
    def delete_face(self):
        """Eliminar rostro"""
        current_item = self.face_list.currentItem()
        if current_item is None:
            self.show_message("Error", "Por favor selecciona un rostro para eliminar", QMessageBox.Warning)
            return
        
        name = current_item.text()
        
        reply = self.show_question(
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar el rostro '{name}'?",
            "Esta acción no se puede deshacer."
        )
        
        if reply == QMessageBox.No:
            return
        
        # Eliminar archivo
        face_path = Path(self.known_faces_dir) / f"{name}{self.get_face_extension(name)}"
        try:
            face_path.unlink()
            
            # Recargar
            self.face_detector.load_known_faces(self.known_faces_dir)
            self.load_face_list()
            
            self.face_preview.clear()
            self.face_preview.setText("Selecciona un rostro o importa una imagen")
            self.name_input.clear()
            self.current_image = None
            
            self.show_message("Éxito", "Rostro eliminado correctamente", QMessageBox.Information)
        except Exception as e:
            self.show_message("Error", f"Error al eliminar: {str(e)}", QMessageBox.Critical)
    
    def import_image(self):
        """Importar imagen desde archivo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen", "",
            "Archivos de Imagen (*.jpg *.jpeg *.png *.bmp)")
        
        if not file_path:
            return
        
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError("No se pudo leer la imagen")
            
            self.current_image = image
            pixmap = numpy_to_pixmap(image)
            
            scaled_pixmap = pixmap.scaled(
                self.face_preview.width() - 40,
                self.face_preview.height() - 40,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.face_preview.setPixmap(scaled_pixmap)
            self.face_preview.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 0.2);
                    border-radius: 8px;
                }
            """)
            
            # Sugerir nombre basado en el archivo
            suggested_name = Path(file_path).stem
            if not self.name_input.text():
                self.name_input.setText(suggested_name)
            
        except Exception as e:
            self.show_message("Error", f"Error al cargar imagen: {str(e)}", QMessageBox.Critical)
            logger.error(f"Error importing image: {e}")
    
    def show_message(self, title, text, icon):
        """Mostrar mensaje con estilo"""
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d3d;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 13px;
            }
            QPushButton {
                background-color: rgba(0, 120, 212, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
        """)
        msg.exec_()
    
    def show_question(self, title, text, informative_text):
        """Mostrar diálogo de confirmación"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setInformativeText(informative_text)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2d2d3d;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 13px;
            }
            QPushButton {
                background-color: rgba(0, 120, 212, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
        """)
        return msg.exec_()