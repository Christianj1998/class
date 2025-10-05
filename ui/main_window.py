import sys
import time
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QTabWidget, QScrollArea, QGridLayout,
                            QMessageBox, QFileDialog, QComboBox, QSlider, QSpinBox,
                            QStackedWidget, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPalette, QColor, QPainter, QLinearGradient, QPen
from loguru import logger
from typing import Dict, Optional, Tuple
import numpy as np
import cv2
from pathlib import Path

from core.face_detection import FaceDetector
from core.camera_manager import CameraManager
from core.alert_system import AlertEvent, AlertSystem
from core.database import FaceDatabase
from core.utils import numpy_to_pixmap, resize_image, draw_face_info
from ui.face_manager import FaceManagerDialog
from ui.alert_panel import AlertPanel
from ui.history_viewer import HistoryViewer


class ModernButton(QPushButton):
    """Botón estilo Windows 11 con efectos hover"""
    def __init__(self, icon_text="", text="", parent=None):
        super().__init__(parent)
        self.icon_text = icon_text
        self.button_text = text
        self.is_active = False
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()
        
    def update_style(self):
        active_bg = "rgba(255, 255, 255, 0.1)" if self.is_active else "transparent"
        self.setStyleSheet(f"""
            ModernButton {{
                background-color: {active_bg};
                border: none;
                border-radius: 8px;
                color: white;
                text-align: left;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
            }}
            ModernButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
            ModernButton:pressed {{
                background-color: rgba(255, 255, 255, 0.05);
            }}
            ModernButton:disabled {{
                background-color: transparent;
                color: rgba(255, 255, 255, 0.3);
            }}
        """)
        
    def set_active(self, active):
        self.is_active = active
        self.update_style()
        
    def setText(self, text):
        self.button_text = text
        super().setText(f"  {self.icon_text}  {text}")


class SidebarWidget(QWidget):
    """Barra lateral estilo Windows 11"""
    page_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.current_index = 0
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedWidth(280)
        
        self.setStyleSheet("""
            SidebarWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(32, 32, 42, 0.95),
                    stop:1 rgba(28, 28, 38, 0.95));
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)
        
        # Logo y título
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)
        
        logo_label = QLabel("🎥")
        logo_label.setStyleSheet("font-size: 32px; padding: 8px;")
        logo_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("Face Recognition")
        title_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 0px 8px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("v1.0.0")
        subtitle_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
            padding: 0px 8px 16px 8px;
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(8)
        
        # Botones de navegación
        self.add_nav_button("📹", "Monitor", 0)
        self.add_nav_button("⚙️", "Controles", 1)
        self.add_nav_button("📊", "Historial", 2)
        self.add_nav_button("👤", "Administrar Rostros", 3)
        self.add_nav_button("🔔", "Alertas", 4)
        
        layout.addStretch()
        
    def add_nav_button(self, icon, text, index):
        btn = ModernButton(icon, text)
        btn.clicked.connect(lambda: self.switch_page(index))
        self.buttons.append(btn)
        self.layout().insertWidget(self.layout().count() - 1, btn)
        
        if index == 0:
            btn.set_active(True)
            
    def switch_page(self, index):
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == index)
        self.current_index = index
        self.page_changed.emit(index)


class ModernCard(QFrame):
    """Tarjeta con efecto acrílico de Windows 11"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            ModernCard {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class MainWindow(QMainWindow):
    def __init__(self, config, auth_manager, database):
        super().__init__()
        self.config = config
        self.auth_manager = auth_manager
        self.database_instance = database
        
        self.setWindowTitle(f"{config['app']['name']} v{config['app']['version']}")
        self.setWindowIcon(QIcon(config['app']['logo']))
        self.setGeometry(100, 100, 1400, 900)
        
        self.processing_interval = 0.5
        
        # Inicializar componentes core
        self.face_detector = FaceDetector(config)
        self.camera_manager = CameraManager('config/camera_config.yaml')
        self.alert_system = AlertSystem(config)
        self.database = FaceDatabase(config['app']['database_path'])
        
        self.face_detector.load_known_faces(config['app']['known_faces_dir'])
        
        # Configurar tema oscuro
        self.setup_theme()
        
        # UI
        self.init_ui()
        
        # Aplicar permisos basados en rol
        self.apply_permissions()
        
        # Mostrar usuario logueado
        self.update_user_display()
        
        # Iniciar cámaras
        self.camera_manager.start_all_cameras()
        
        # Timer de actualización
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(30)
        
        self.last_processed: Dict[int, float] = {}
        
    def apply_permissions(self):
        """Apply UI restrictions based on user role"""
        user = self.auth_manager.get_current_user()
        if not user:
            return
        
        logger.info(f"Applying permissions for role: {user.role}")
        
        # Viewer: solo puede ver cámaras, sin control
        if user.role == 'viewer':
            # Deshabilitar controles de cámara
            if hasattr(self, 'start_btn'):
                self.start_btn.setEnabled(False)
                self.start_btn.setToolTip("Permission denied: Viewers cannot control cameras")
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setEnabled(False)
                self.stop_btn.setToolTip("Permission denied: Viewers cannot control cameras")
            
            # Deshabilitar controles de configuración
            if hasattr(self, 'threshold_slider'):
                self.threshold_slider.setEnabled(False)
            if hasattr(self, 'interval_spin'):
                self.interval_spin.setEnabled(False)
            
            # Deshabilitar gestión de rostros
            if hasattr(self, 'sidebar') and len(self.sidebar.buttons) > 3:
                self.sidebar.buttons[3].setEnabled(False)
                self.sidebar.buttons[3].setToolTip("Permission denied: Viewers cannot manage faces")
        
        # Operator: puede controlar cámaras y gestionar rostros
        elif user.role == 'operator':
            pass  # Tiene acceso a casi todo
        
        # Admin: acceso completo
        elif user.role == 'admin':
            pass  # Sin restricciones
    
    def update_user_display(self):
        """Display current user info in status bar"""
        user = self.auth_manager.get_current_user()
        if user:
            role_icons = {
                'admin': '👑',
                'operator': '⚙️',
                'viewer': '👁️'
            }
            icon = role_icons.get(user.role, '👤')
            user_info = QLabel(f"{icon} {user.username} ({user.role})")
            user_info.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 0 10px;")
            self.statusBar().addPermanentWidget(user_info)
            
            # Botón de logout
            logout_btn = QPushButton("Logout")
            logout_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(220, 53, 69, 0.8);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(220, 53, 69, 1);
                }
            """)
            logout_btn.clicked.connect(self.handle_logout)
            self.statusBar().addPermanentWidget(logout_btn)
    
    def handle_logout(self):
        """Handle user logout"""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            user = self.auth_manager.get_current_user()
            if user:
                logger.info(f"User {user.username} logged out")
            self.close()

    def setup_theme(self):
        """Configurar tema oscuro estilo Windows 11"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16213e);
            }
            QLabel {
                color: white;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QPushButton {
                background-color: rgba(0, 120, 212, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 100, 180, 1);
            }
            QPushButton:disabled {
                background-color: rgba(0, 120, 212, 0.3);
                color: rgba(255, 255, 255, 0.4);
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(32, 32, 42, 0.98);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: rgba(0, 120, 212, 0.5);
                border-radius: 6px;
                padding: 4px;
            }
            QSlider::groove:horizontal {
                background-color: rgba(255, 255, 255, 0.1);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background-color: #0078d4;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #1e90ff;
            }
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QSpinBox:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barra lateral
        self.sidebar = SidebarWidget()
        self.sidebar.page_changed.connect(self.switch_page)
        main_layout.addWidget(self.sidebar)
        
        # Área de contenido
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)
        
        # Páginas
        self.setup_monitor_page()
        self.setup_controls_page()
        self.setup_history_page()
        self.setup_face_manager_page()
        self.setup_alerts_page()
        
        # Status bar moderno
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: rgba(32, 32, 42, 0.8);
                color: rgba(255, 255, 255, 0.7);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                font-size: 12px;
                padding: 4px 16px;
            }
        """)
        self.status_label = QLabel("Sistema listo")
        self.statusBar().addWidget(self.status_label)
        
    def setup_monitor_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Título
        title = QLabel("Monitor de Cámaras")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: white;
            margin-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Scroll para cámaras
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        self.camera_container = QWidget()
        self.camera_grid = QGridLayout(self.camera_container)
        self.camera_grid.setSpacing(20)
        
        scroll.setWidget(self.camera_container)
        layout.addWidget(scroll)
        
        # Agregar labels de cámaras en tarjetas
        self.camera_labels = {}
        for cam_id in self.camera_manager.cameras:
            card = ModernCard()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)
            
            cam_label = QLabel()
            cam_label.setAlignment(Qt.AlignCenter)
            cam_label.setMinimumSize(500, 375)
            cam_label.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
            """)
            
            cam_title = QLabel(f"📹 Cámara {cam_id}")
            cam_title.setStyleSheet("""
                font-size: 14px;
                font-weight: 600;
                color: white;
                padding: 8px;
            """)
            
            card_layout.addWidget(cam_label)
            card_layout.addWidget(cam_title)
            
            self.camera_labels[cam_id] = cam_label
            self.camera_grid.addWidget(card, (cam_id // 2), (cam_id % 2))
        
        self.content_stack.addWidget(page)
        
    def setup_controls_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Título
        title = QLabel("Panel de Control")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: white;
            margin-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Tarjeta de control de cámaras
        camera_card = ModernCard()
        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setSpacing(16)
        
        cam_title = QLabel("🎥 Control de Cámaras")
        cam_title.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        camera_layout.addWidget(cam_title)
        
        self.camera_combo = QComboBox()
        for cam_id, cam_config in self.camera_manager.cameras.items():
            self.camera_combo.addItem(f"Cámara {cam_id}: {cam_config.name}", cam_id)
        camera_layout.addWidget(self.camera_combo)
        
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Iniciar")
        self.start_btn.clicked.connect(self.start_selected_camera)
        self.stop_btn = QPushButton("⏸️ Detener")
        self.stop_btn.clicked.connect(self.stop_selected_camera)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        camera_layout.addLayout(btn_layout)
        
        layout.addWidget(camera_card)
        
        # Tarjeta de configuración
        config_card = ModernCard()
        config_layout = QVBoxLayout(config_card)
        config_layout.setSpacing(16)
        
        config_title = QLabel("⚙️ Configuración de Reconocimiento")
        config_title.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        config_layout.addWidget(config_title)
        
        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Umbral de Reconocimiento:")
        threshold_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        threshold_layout.addWidget(threshold_label)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(50, 100)
        self.threshold_slider.setValue(int(self.config['recognition']['recognition_threshold'] * 100))
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        threshold_layout.addWidget(self.threshold_slider)
        
        self.threshold_value = QLabel(f"{self.threshold_slider.value() / 100:.2f}")
        self.threshold_value.setStyleSheet("color: #0078d4; font-weight: bold; min-width: 40px;")
        threshold_layout.addWidget(self.threshold_value)
        
        config_layout.addLayout(threshold_layout)
        
        # Intervalo de procesamiento
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Intervalo de Procesamiento (ms):")
        interval_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        interval_layout.addWidget(interval_label)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 5000)
        self.interval_spin.setValue(int(self.processing_interval * 1000))
        self.interval_spin.valueChanged.connect(self.update_processing_interval)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        
        config_layout.addLayout(interval_layout)
        
        layout.addWidget(config_card)
        
        # Tarjeta de estado
        status_card = ModernCard()
        status_layout = QVBoxLayout(status_card)
        
        status_title = QLabel("📊 Estado del Sistema")
        status_title.setStyleSheet("font-size: 18px; font-weight: 600; color: white;")
        status_layout.addWidget(status_title)
        
        self.status_display = QLabel("Cargando...")
        self.status_display.setWordWrap(True)
        self.status_display.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 13px; line-height: 1.5;")
        status_layout.addWidget(self.status_display)
        
        layout.addWidget(status_card)
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def setup_history_page(self):
        self.history_viewer = HistoryViewer(self.database, self.config)
        self.content_stack.addWidget(self.history_viewer)
        
    def setup_face_manager_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = QLabel("Administración de Rostros")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: white; margin-bottom: 16px;")
        layout.addWidget(title)
        
        btn_layout = QHBoxLayout()
        
        face_btn = QPushButton("Gestionar Rostros Conocidos")
        face_btn.clicked.connect(self.open_face_manager)
        face_btn.setFixedWidth(300)
        btn_layout.addWidget(face_btn)
        
        # Botón de gestión de usuarios (solo admin)
        user = self.auth_manager.get_current_user()
        if user and user.role == 'admin':
            user_btn = QPushButton("Gestionar Usuarios")
            user_btn.clicked.connect(self.open_user_manager)
            user_btn.setFixedWidth(300)
            user_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(108, 92, 231, 0.8);
                }
                QPushButton:hover {
                    background-color: rgba(108, 92, 231, 1);
                }
            """)
            btn_layout.addWidget(user_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def setup_alerts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        
        title = QLabel("Panel de Alertas")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: white; margin-bottom: 16px;")
        layout.addWidget(title)
        
        btn = QPushButton("Abrir Panel de Alertas")
        btn.clicked.connect(self.open_alert_panel)
        btn.setFixedWidth(300)
        layout.addWidget(btn)
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        
    def open_face_manager(self):
        if not self.auth_manager.has_permission('operator'):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "Only operators and administrators can manage faces."
            )
            return
        
        dialog = FaceManagerDialog(self.face_detector, self.config['app']['known_faces_dir'])
        dialog.exec_()
        self.face_detector.load_known_faces(self.config['app']['known_faces_dir'])
    
    def open_user_manager(self):
        """Open user management dialog (admin only)"""
        if not self.auth_manager.has_permission('admin'):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "Only administrators can manage users."
            )
            return
        
        from ui.user_management import UserManagementDialog
        dialog = UserManagementDialog(self.database, self.auth_manager, self)
        dialog.exec_()
        
    def open_alert_panel(self):
        dialog = AlertPanel(self.alert_system)
        dialog.exec_()
        
    def start_selected_camera(self):
        cam_id = self.camera_combo.currentData()
        if self.camera_manager.start_camera(cam_id):
            self.status_label.setText(f"✅ Cámara {cam_id} iniciada")
            
    def stop_selected_camera(self):
        cam_id = self.camera_combo.currentData()
        if self.camera_manager.stop_camera(cam_id):
            self.status_label.setText(f"⏸️ Cámara {cam_id} detenida")
            
    def update_threshold(self, value):
        threshold = value / 100
        self.face_detector.recognition_threshold = threshold
        self.threshold_value.setText(f"{threshold:.2f}")
        
    def update_processing_interval(self, value):
        self.processing_interval = value / 1000
        
    def update(self):
        try:
            # Check if session is still valid
            if not self.auth_manager.is_authenticated():
                logger.warning("Session expired, closing application")
                QMessageBox.warning(
                    self,
                    "Session Expired",
                    "Your session has expired. Please login again."
                )
                self.close()
                return
            
            frames = self.camera_manager.get_all_frames()
            
            for cam_id, frame in frames.items():
                if frame is None:
                    continue
                    
                current_time = time.time()
                last_time = self.last_processed.get(cam_id, 0)
                if current_time - last_time < self.processing_interval:
                    self.display_frame(cam_id, frame)
                    continue
                    
                processed_frame, alert_triggered = self.process_frame(cam_id, frame)
                self.display_frame(cam_id, processed_frame)
                self.last_processed[cam_id] = current_time
                
            self.update_status()
            
        except Exception as e:
            logger.error(f"Error in update loop: {e}")
            self.status_label.setText(f"❌ Error: {str(e)}")
            
    def process_frame(self, cam_id: int, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        alert_triggered = False
        try:
            faces = self.face_detector.detect_faces(frame)
            if not faces:
                return frame, False
                
            recognized_faces = self.face_detector.recognize_faces(faces)
            
            for face, known_face, confidence in recognized_faces:
                camera_name = self.camera_manager.cameras[cam_id].name
                
                if known_face:
                    frame = draw_face_info(
                        frame, face.bbox,
                        name=known_face.name,
                        confidence=confidence,
                        camera_name=camera_name,
                        age=face.age,
                        gender=face.gender,
                        timestamp=time.time()
                    )
                    
                    alert_event = self.alert_system.trigger_alert(
                        cam_id, camera_name,
                        known_face.name, face, confidence,
                        frame
                    )
                    alert_triggered = True
                    
                    # Incluir user_id en el log
                    user = self.auth_manager.get_current_user()
                    self.database.log_face_event(
                        alert_event,
                        user_id=user.id if user else None
                    )
                else:
                    frame = draw_face_info(
                        frame, face.bbox,
                        name="Desconocido",
                        confidence=confidence,
                        camera_name=camera_name,
                        timestamp=time.time()
                    )
                    
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            
        return frame, alert_triggered
        
    def display_frame(self, cam_id: int, frame: np.ndarray):
        try:
            if frame is None:
                return
                
            pixmap = numpy_to_pixmap(frame)
            self.camera_labels[cam_id].setPixmap(
                pixmap.scaled(self.camera_labels[cam_id].size(), 
                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
            
    def update_status(self):
        try:
            status_text = []
            
            # User info
            user = self.auth_manager.get_current_user()
            if user:
                status_text.append(f"👤 <b>Logged in as:</b> {user.username} ({user.role})")
            
            status_text.append("<br>📹 <b>Estado de Cámaras</b>")
            for cam_id, cam_config in self.camera_manager.cameras.items():
                running = cam_id in self.camera_manager.capture_threads
                icon = "🟢" if running else "🔴"
                status_text.append(f"{icon} Cámara {cam_id} ({cam_config.name}): {'Activa' if running else 'Detenida'}")
                
            status_text.append("<br>👤 <b>Base de Datos</b>")
            status_text.append(f"Rostros conocidos: {len(self.face_detector.known_faces)}")
            
            status_text.append("<br>🔔 <b>Alertas Recientes</b>")
            recent_alerts = self.alert_system.get_recent_alerts(3)
            if recent_alerts:
                for alert in recent_alerts:
                    time_str = time.strftime("%H:%M:%S", time.localtime(alert.timestamp))
                    status_text.append(f"• {time_str}: {alert.face_name} en {alert.camera_name} ({alert.confidence:.2f})")
            else:
                status_text.append("Sin alertas recientes")
                
            self.status_display.setText("<br>".join(status_text))
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            
    def closeEvent(self, event):
        try:
            user = self.auth_manager.get_current_user()
            if user:
                logger.info(f"Application closing - User: {user.username}")
            
            self.camera_manager.stop_all_cameras()
            self.update_timer.stop()
            event.accept()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            event.accept()