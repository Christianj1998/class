import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QFileDialog, QMessageBox, QLineEdit, QComboBox, 
                            QFrame, QSplitter, QListWidgetItem, QGraphicsDropShadowEffect,
                            QSpinBox, QDateEdit, QScrollArea)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QPixmap, QFont, QColor, QIcon
from loguru import logger
import cv2
import numpy as np
from pathlib import Path

from core.utils import numpy_to_pixmap, resize_image

class FaceManagerDialog(QDialog):
    def __init__(self, face_detector, known_faces_dir, database, auth_manager):
        super().__init__()
        self.face_detector = face_detector
        self.known_faces_dir = known_faces_dir
        self.database = database
        self.auth_manager = auth_manager
        self.current_image = None
        self.selected_face_data = None
        
        self.setWindowTitle("Administrador de Rostros")
        self.setGeometry(150, 100, 1100, 800)
        self.setMinimumSize(900, 700)
        
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
            QSpinBox, QDateEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QSpinBox:focus, QDateEdit:focus {
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
        self.face_preview.setMinimumSize(400, 300)
        self.face_preview.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
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
        
        # Información del rostro - Scroll area para formulario largo
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        info_widget = QFrame()
        info_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)
        
        # Nombre
        name_label = QLabel("Nombre:")
        name_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ingresa el nombre de la persona...")
        info_layout.addWidget(self.name_input)
        
        # Apellido
        surname_label = QLabel("Apellido:")
        surname_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(surname_label)
        
        self.surname_input = QLineEdit()
        self.surname_input.setPlaceholderText("Ingresa el apellido...")
        info_layout.addWidget(self.surname_input)
        
        # Edad
        age_label = QLabel("Edad:")
        age_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(age_label)
        
        self.age_input = QSpinBox()
        self.age_input.setRange(0, 120)
        info_layout.addWidget(self.age_input)
        
        # Cédula
        cedula_label = QLabel("Cédula:")
        cedula_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(cedula_label)
        
        self.cedula_input = QLineEdit()
        self.cedula_input.setPlaceholderText("Número de cédula...")
        info_layout.addWidget(self.cedula_input)
        
        # Fecha de Nacimiento
        birth_label = QLabel("Fecha de Nacimiento:")
        birth_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(birth_label)
        
        self.birth_input = QDateEdit()
        self.birth_input.setCalendarPopup(True)
        self.birth_input.setDate(QDate.currentDate())
        info_layout.addWidget(self.birth_input)
        
        # Delito
        crime_label = QLabel("Delito:")
        crime_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(crime_label)
        
        self.crime_input = QLineEdit()
        self.crime_input.setPlaceholderText("Descripción del delito...")
        info_layout.addWidget(self.crime_input)
        
        # Número de Expediente
        case_label = QLabel("Número de Expediente:")
        case_label.setStyleSheet("font-weight: 600; color: white;")
        info_layout.addWidget(case_label)
        
        self.case_input = QLineEdit()
        self.case_input.setPlaceholderText("Número de expediente...")
        info_layout.addWidget(self.case_input)
        
        scroll_area.setWidget(info_widget)
        right_layout.addWidget(scroll_area)
        
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
        """Cargar lista de rostros desde la base de datos"""
        self.face_list.clear()
        
        try:
            known_faces = self.database.get_known_faces()
            
            for face_data in known_faces:
                display_text = f"👤 {face_data['name']} {face_data['lastname']} - Cédula: {face_data['cedula']}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, face_data)
                self.face_list.addItem(item)
            
            count = len(known_faces)
            self.face_count_label.setText(f"{count} rostro{'s' if count != 1 else ''} registrado{'s' if count != 1 else ''}")
            
            logger.info(f"Loaded {count} faces from database")
            
        except Exception as e:
            logger.error(f"Error loading faces from database: {e}")
            self.show_message("Error", f"Error al cargar rostros: {str(e)}", QMessageBox.Critical)
        
    def on_face_selected(self, current, previous):
        """Manejar selección de rostro"""
        if current is None:
            self.face_preview.clear()
            self.face_preview.setText("Selecciona un rostro o importa una imagen")
            self.clear_all_fields()
            self.selected_face_data = None
            return
        
        try:
            face_data = current.data(Qt.UserRole)
            self.selected_face_data = face_data
            
            # Llenar campos
            self.name_input.setText(face_data['name'])
            self.surname_input.setText(face_data['lastname'])
            self.age_input.setValue(face_data['age'])
            self.cedula_input.setText(face_data['cedula'])
            
            birth_date = QDate.fromString(face_data['birth_date'], "yyyy-MM-dd")
            if birth_date.isValid():
                self.birth_input.setDate(birth_date)
            
            self.crime_input.setText(face_data['crime'])
            self.case_input.setText(face_data['case_number'])
            
            # Cargar y mostrar imagen
            face_path = Path(face_data['image_path'])
            if not face_path.exists():
                self.face_preview.setText("📷 Archivo de imagen no encontrado")
                return
            
            image = cv2.imread(str(face_path))
            if image is None:
                self.face_preview.setText("❌ Error al cargar la imagen")
                return
            
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
            
        except Exception as e:
            logger.error(f"Error loading face data: {e}")
            self.show_message("Error", f"Error al cargar datos del rostro: {str(e)}", QMessageBox.Critical)
    
    def add_face(self):
        """Agregar nuevo rostro"""
        name = self.name_input.text().strip()
        surname = self.surname_input.text().strip()
        age = self.age_input.value()
        cedula = self.cedula_input.text().strip()
        birth_date = self.birth_input.date().toString("yyyy-MM-dd")
        crime = self.crime_input.text().strip()
        case_number = self.case_input.text().strip()
        
        # Validaciones
        if not name:
            self.show_message("Error", "Por favor ingresa un nombre", QMessageBox.Warning)
            return
        
        if not surname:
            self.show_message("Error", "Por favor ingresa un apellido", QMessageBox.Warning)
            return
        
        if not cedula:
            self.show_message("Error", "La cédula es obligatoria", QMessageBox.Warning)
            return
        
        if self.current_image is None:
            self.show_message("Error", "Por favor importa o selecciona una imagen primero", QMessageBox.Warning)
            return
        
        # Verificar si la cédula ya existe
        existing_faces = self.database.get_known_faces()
        for face in existing_faces:
            if face['cedula'] == cedula:
                self.show_message("Error", f"Ya existe un rostro con la cédula '{cedula}'", QMessageBox.Warning)
                return
        
        # Agregar el rostro
        user = self.auth_manager.get_current_user()
        success = self.face_detector.add_known_face(
            self.current_image, name, surname, age, cedula,
            birth_date, crime, case_number,
            self.known_faces_dir, self.database,
            created_by=user.id if user else None
        )
        
        if success:
            self.show_message("Éxito", 
                             f"Rostro de {name} {surname} agregado correctamente", 
                             QMessageBox.Information)
            self.clear_all_fields()
            self.load_face_list()
        else:
            self.show_message("Error", "No se pudo agregar el rostro", QMessageBox.Critical)
    
    def update_face(self):
        """Actualizar rostro existente"""
        if not self.selected_face_data:
            self.show_message("Error", "Por favor selecciona un rostro para actualizar", QMessageBox.Warning)
            return
        
        name = self.name_input.text().strip()
        surname = self.surname_input.text().strip()
        age = self.age_input.value()
        cedula = self.cedula_input.text().strip()
        birth_date = self.birth_input.date().toString("yyyy-MM-dd")
        crime = self.crime_input.text().strip()
        case_number = self.case_input.text().strip()
        
        if not name or not surname:
            self.show_message("Error", "Nombre y apellido son obligatorios", QMessageBox.Warning)
            return
        
        try:
            import sqlite3
            
            # CORRECCIÓN: Usar el path correcto de la base de datos
            conn = sqlite3.connect(str(self.database.db_path))
            cursor = conn.cursor()
            
            # Actualizar el registro
            cursor.execute('''
                UPDATE known_faces 
                SET name=?, lastname=?, age=?, birth_date=?, crime=?, case_number=?
                WHERE cedula=?
            ''', (name, surname, age, birth_date, crime, case_number, cedula))
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected_rows > 0:
                # Recargar rostros en el detector
                self.face_detector.load_known_faces_from_db(self.database)
                
                self.show_message("Éxito", "Rostro actualizado correctamente", QMessageBox.Information)
                self.load_face_list()
            else:
                self.show_message("Error", "No se encontró el rostro para actualizar", QMessageBox.Warning)
            
        except Exception as e:
            logger.error(f"Error updating face: {e}")
            self.show_message("Error", f"Error al actualizar: {str(e)}", QMessageBox.Critical)
           

    def delete_face(self):
        """Eliminar rostro"""
        if not self.selected_face_data:
            self.show_message("Error", "Por favor selecciona un rostro para eliminar", QMessageBox.Warning)
            return
        
        cedula = self.selected_face_data['cedula']
        name = f"{self.selected_face_data['name']} {self.selected_face_data['lastname']}"
        
        reply = self.show_question(
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar el rostro de {name}?",
            "Esta acción no se puede deshacer."
        )
        
        if reply == QMessageBox.No:
            return
        
        try:
            user = self.auth_manager.get_current_user()
            success = self.database.delete_known_face(
                cedula,
                deleted_by=user.id if user else None
            )
            
            if success:
                self.face_detector.load_known_faces_from_db(self.database)
                self.load_face_list()
                self.clear_all_fields()
                
                self.show_message("Éxito", "Rostro eliminado correctamente", QMessageBox.Information)
            else:
                self.show_message("Error", "No se pudo eliminar el rostro", QMessageBox.Critical)
                
        except Exception as e:
            logger.error(f"Error deleting face: {e}")
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
            
        except Exception as e:
            self.show_message("Error", f"Error al cargar imagen: {str(e)}", QMessageBox.Critical)
            logger.error(f"Error importing image: {e}")
    
    def clear_all_fields(self):
        """Limpiar todos los campos del formulario"""
        self.name_input.clear()
        self.surname_input.clear()
        self.age_input.setValue(0)
        self.cedula_input.clear()
        self.birth_input.setDate(QDate.currentDate())
        self.crime_input.clear()
        self.case_input.clear()
        self.face_preview.clear()
        self.face_preview.setText("Selecciona un rostro o importa una imagen")
        self.current_image = None
        self.selected_face_data = None
    
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