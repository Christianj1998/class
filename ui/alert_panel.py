from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QCheckBox, QMessageBox, QListWidgetItem, QFrame,
                            QGraphicsDropShadowEffect, QScrollArea, QWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPixmap, QCursor
from loguru import logger
import time
from pathlib import Path
import cv2
from datetime import datetime

class AlertDetailDialog(QDialog):
    """Ventana emergente con información detallada del registro en formato card"""
    
    def __init__(self, alert_event, parent=None):
        super().__init__(parent)
        self.alert_event = alert_event
        self.setWindowTitle(f"Detalle - {alert_event.face_name}")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        
        self.setup_style()
        self.init_ui()
        
    def setup_style(self):
        """Estilo moderno Windows 11"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16213e);
            }
            QLabel {
                color: white;
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
            QPushButton#closeButton {
                background-color: rgba(220, 53, 69, 0.8);
            }
            QPushButton#closeButton:hover {
                background-color: rgba(220, 53, 69, 1);
            }
        """)
    
    def init_ui(self):
        """Crear interfaz con cards"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Scroll area para todo el contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # Header Card
        header_card = self.create_header_card()
        content_layout.addWidget(header_card)
        
        # Image Card
        if self.alert_event.screenshot_path:
            image_card = self.create_image_card()
            content_layout.addWidget(image_card)
        
        # Info Card
        info_card = self.create_info_card()
        content_layout.addWidget(info_card)
        
        # Biometric Card (edad y género)
        if self.alert_event.age or self.alert_event.gender:
            bio_card = self.create_biometric_card()
            content_layout.addWidget(bio_card)
        
        # Location Card
        location_card = self.create_location_card()
        content_layout.addWidget(location_card)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(150)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    
    def create_card(self, title, icon=""):
        """Crear card base con estilo"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        # Title
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: white;
            margin-bottom: 8px;
        """)
        card_layout.addWidget(title_label)
        
        return card, card_layout
    
    def create_header_card(self):
        """Card de header con nombre y estado"""
        card, layout = self.create_card("Identificación", "🆔")
        
        # Nombre grande
        name_label = QLabel(self.alert_event.face_name)
        name_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
            margin: 10px 0;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # Badge de confianza
        confidence_pct = self.alert_event.confidence * 100 if self.alert_event.confidence <= 1 else self.alert_event.confidence
        
        confidence_frame = QFrame()
        confidence_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {'rgba(76, 175, 80, 0.3)' if confidence_pct >= 80 else 'rgba(255, 193, 7, 0.3)' if confidence_pct >= 60 else 'rgba(244, 67, 54, 0.3)'};
                border-radius: 20px;
                padding: 8px 20px;
            }}
        """)
        confidence_layout = QHBoxLayout(confidence_frame)
        confidence_layout.setContentsMargins(0, 0, 0, 0)
        
        confidence_label = QLabel(f"🎯 Confianza: {confidence_pct:.1f}%")
        confidence_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: white;
        """)
        confidence_label.setAlignment(Qt.AlignCenter)
        confidence_layout.addWidget(confidence_label)
        
        layout.addWidget(confidence_frame, alignment=Qt.AlignCenter)
        
        return card
    
    def create_image_card(self):
        """Card con la imagen capturada"""
        card, layout = self.create_card("Captura de Cámara", "📷")
        
        # Cargar imagen
        screenshot_path = Path(self.alert_event.screenshot_path)
        if screenshot_path.exists():
            try:
                image = cv2.imread(str(screenshot_path))
                if image is not None:
                    # Convertir a RGB
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    h, w, ch = image_rgb.shape
                    bytes_per_line = ch * w
                    
                    from PyQt5.QtGui import QImage
                    q_image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)
                    
                    # Image label
                    image_label = QLabel()
                    image_label.setPixmap(pixmap.scaled(
                        700, 400,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    ))
                    image_label.setAlignment(Qt.AlignCenter)
                    image_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(0, 0, 0, 0.3);
                            border-radius: 8px;
                            padding: 10px;
                        }
                    """)
                    layout.addWidget(image_label)
                    
                    # Info de la imagen
                    img_info = QLabel(f"📐 Resolución: {w}x{h} | 📄 {screenshot_path.name}")
                    img_info.setStyleSheet("""
                        font-size: 11px;
                        color: rgba(255, 255, 255, 0.6);
                        margin-top: 8px;
                    """)
                    img_info.setAlignment(Qt.AlignCenter)
                    layout.addWidget(img_info)
                    
            except Exception as e:
                logger.error(f"Error loading image: {e}")
                error_label = QLabel("❌ Error al cargar la imagen")
                error_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)
        else:
            no_image_label = QLabel("📷 Imagen no disponible")
            no_image_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 14px;")
            no_image_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_image_label)
        
        return card
    
    def create_info_card(self):
        """Card con información general"""
        card, layout = self.create_card("Información del Evento", "ℹ️")
        
        # Timestamp
        time_str = datetime.fromtimestamp(self.alert_event.timestamp).strftime("%d/%m/%Y %H:%M:%S")
        
        info_items = [
            ("🕒", "Fecha y Hora", time_str),
            ("📹", "Cámara", f"{self.alert_event.camera_name} (ID: {self.alert_event.camera_id})"),
            ("👤", "Persona Identificada", self.alert_event.face_name),
        ]
        
        for icon, label_text, value in info_items:
            item_frame = QFrame()
            item_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.03);
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
            item_layout = QHBoxLayout(item_frame)
            
            # Icon + Label
            label = QLabel(f"{icon} <b>{label_text}:</b>")
            label.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.8);")
            item_layout.addWidget(label)
            
            item_layout.addStretch()
            
            # Value
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 13px; color: white; font-weight: 600;")
            item_layout.addWidget(value_label)
            
            layout.addWidget(item_frame)
        
        return card
    
    def create_biometric_card(self):
        """Card con datos biométricos"""
        card, layout = self.create_card("Datos Biométricos", "🧬")
        
        bio_layout = QHBoxLayout()
        
        # Age
        if self.alert_event.age:
            age_frame = QFrame()
            age_frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(33, 150, 243, 0.3),
                        stop:1 rgba(33, 150, 243, 0.1));
                    border-radius: 12px;
                    padding: 20px;
                }
            """)
            age_layout = QVBoxLayout(age_frame)
            
            age_icon = QLabel("👶")
            age_icon.setStyleSheet("font-size: 32px;")
            age_icon.setAlignment(Qt.AlignCenter)
            age_layout.addWidget(age_icon)
            
            age_label = QLabel(f"{self.alert_event.age}")
            age_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
            age_label.setAlignment(Qt.AlignCenter)
            age_layout.addWidget(age_label)
            
            age_text = QLabel("Años (estimado)")
            age_text.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.7);")
            age_text.setAlignment(Qt.AlignCenter)
            age_layout.addWidget(age_text)
            
            bio_layout.addWidget(age_frame)
        
        # Gender
        if self.alert_event.gender:
            gender_frame = QFrame()
            gender_color = "rgba(233, 30, 99, 0.3)" if self.alert_event.gender == "Female" else "rgba(3, 169, 244, 0.3)"
            gender_frame.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {gender_color},
                        stop:1 rgba(255, 255, 255, 0.05));
                    border-radius: 12px;
                    padding: 20px;
                }}
            """)
            gender_layout = QVBoxLayout(gender_frame)
            
            gender_icon = QLabel("🚻")
            gender_icon.setStyleSheet("font-size: 32px;")
            gender_icon.setAlignment(Qt.AlignCenter)
            gender_layout.addWidget(gender_icon)
            
            gender_label = QLabel(self.alert_event.gender)
            gender_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
            gender_label.setAlignment(Qt.AlignCenter)
            gender_layout.addWidget(gender_label)
            
            gender_text = QLabel("Género (detectado)")
            gender_text.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.7);")
            gender_text.setAlignment(Qt.AlignCenter)
            gender_layout.addWidget(gender_text)
            
            bio_layout.addWidget(gender_frame)
        
        layout.addLayout(bio_layout)
        return card
    
    def create_location_card(self):
        """Card con información de ubicación"""
        card, layout = self.create_card("Ubicación de la Detección", "📍")
        
        # Mapa visual simple
        location_frame = QFrame()
        location_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(76, 175, 80, 0.2),
                    stop:1 rgba(76, 175, 80, 0.05));
                border-radius: 8px;
                padding: 16px;
            }
        """)
        location_layout = QVBoxLayout(location_frame)
        
        camera_info = QLabel(f"🎥 <b>{self.alert_event.camera_name}</b>")
        camera_info.setStyleSheet("font-size: 16px; color: white;")
        location_layout.addWidget(camera_info)
        
        camera_id_info = QLabel(f"ID de Cámara: {self.alert_event.camera_id}")
        camera_id_info.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.7);")
        location_layout.addWidget(camera_id_info)
        
        layout.addWidget(location_frame)
        
        # File path si existe
        if self.alert_event.screenshot_path:
            path_label = QLabel(f"💾 Archivo: {Path(self.alert_event.screenshot_path).name}")
            path_label.setStyleSheet("""
                font-size: 11px;
                color: rgba(255, 255, 255, 0.5);
                margin-top: 8px;
            """)
            path_label.setWordWrap(True)
            layout.addWidget(path_label)
        
        return card


class ClickableAlertItem(QListWidgetItem):
    """Item de lista clickeable personalizado"""
    
    def __init__(self, alert_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_event = alert_event
        
        # Estilo de cursor
        self.setFlags(self.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)


class AlertPanel(QDialog):
    def __init__(self, alert_system):
        super().__init__()
        self.alert_system = alert_system
        self.setWindowTitle("Panel de Alertas")
        self.setGeometry(300, 300, 900, 600)
        self.setMinimumSize(800, 500)
        
        self.setup_style()
        self.init_ui()
        self.load_alerts()
        
    def setup_style(self):
        """Estilo moderno Windows 11"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16213e);
            }
            QLabel {
                color: white;
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
                padding: 12px;
                margin: 4px 0;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 120, 212, 0.2);
                border: 1px solid rgba(0, 120, 212, 0.4);
                cursor: pointer;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.3);
                border: 1px solid rgba(0, 120, 212, 0.5);
            }
            QCheckBox {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
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
            QPushButton#clearButton {
                background-color: rgba(220, 53, 69, 0.8);
            }
            QPushButton#clearButton:hover {
                background-color: rgba(220, 53, 69, 1);
            }
        """)
        
    def init_ui(self):
        """Set up and arrange all the UI widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 8px;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("🔔 Panel de Alertas")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Haz clic en cualquier alerta para ver detalles completos")
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_frame)
        
        # Counter label
        self.count_label = QLabel()
        self.count_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
            font-weight: 600;
            padding: 8px 0;
        """)
        layout.addWidget(self.count_label)
        
        # Alert list
        self.alert_list = QListWidget()
        self.alert_list.itemClicked.connect(self.on_alert_clicked)
        layout.addWidget(self.alert_list)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.enable_alerts_check = QCheckBox("Habilitar Alertas Sonoras")
        self.enable_alerts_check.setChecked(self.alert_system.alert_enabled)
        self.enable_alerts_check.stateChanged.connect(self.toggle_alerts)
        controls_layout.addWidget(self.enable_alerts_check)
        
        self.enable_screenshots_check = QCheckBox("Captura Automática")
        self.enable_screenshots_check.setChecked(self.alert_system.screenshot_enabled)
        self.enable_screenshots_check.stateChanged.connect(self.toggle_screenshots)
        controls_layout.addWidget(self.enable_screenshots_check)
        
        controls_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Actualizar")
        self.refresh_btn.clicked.connect(self.load_alerts)
        controls_layout.addWidget(self.refresh_btn)
        
        self.clear_btn = QPushButton("🗑️ Limpiar")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self.clear_alerts)
        controls_layout.addWidget(self.clear_btn)
        
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        controls_layout.addWidget(self.close_btn)
        
        layout.addLayout(controls_layout)
        
    def load_alerts(self):
        """Fetch and display alerts"""
        self.alert_list.clear()
        alerts = self.alert_system.get_recent_alerts(50)
        
        self.count_label.setText(f"📋 Total de alertas: {len(alerts)}")
        
        if not alerts:
            item = QListWidgetItem("📭 No hay alertas para mostrar")
            item.setFlags(Qt.ItemIsEnabled)
            self.alert_list.addItem(item)
            return
        
        for alert in alerts:
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert.timestamp))
            confidence_pct = alert.confidence * 100 if alert.confidence <= 1 else alert.confidence
            
            # Crear texto con formato mejorado
            item_text = f"🕒 {time_str}  |  👤 {alert.face_name}  |  📹 {alert.camera_name}  |  🎯 {confidence_pct:.1f}%"
            
            # Agregar info biométrica si existe
            bio_info = []
            if alert.age:
                bio_info.append(f"👶 {alert.age} años")
            if alert.gender:
                bio_info.append(f"🚻 {alert.gender}")
            
            if bio_info:
                item_text += f"\n   {' | '.join(bio_info)}"
            
            # Crear item clickeable
            item = ClickableAlertItem(alert, item_text)
            
            # Color según confianza
            if confidence_pct >= 80:
                item.setForeground(QColor(76, 175, 80))  # Verde
            elif confidence_pct >= 60:
                item.setForeground(QColor(255, 193, 7))  # Amarillo
            else:
                item.setForeground(QColor(244, 67, 54))  # Rojo
            
            self.alert_list.addItem(item)
            
    def on_alert_clicked(self, item):
        """Handle alert click - show detail dialog"""
        if isinstance(item, ClickableAlertItem):
            try:
                detail_dialog = AlertDetailDialog(item.alert_event, self)
                detail_dialog.exec_()
            except Exception as e:
                logger.error(f"Error showing alert detail: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo mostrar el detalle de la alerta:\n{str(e)}"
                )
            
    def toggle_alerts(self, state):
        """Enable or disable alerts"""
        enabled = state == Qt.Checked
        self.alert_system.enable_alerts(enabled)
        status = "activadas" if enabled else "desactivadas"
        logger.info(f"Alertas sonoras {status}")
        
    def toggle_screenshots(self, state):
        """Enable or disable screenshots"""
        enabled = state == Qt.Checked
        self.alert_system.enable_screenshots(enabled)
        status = "activada" if enabled else "desactivada"
        logger.info(f"Captura automática {status}")
        
    def clear_alerts(self):
        """Clear all alerts after confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirmar Limpieza",
            "¿Estás seguro de que deseas eliminar todas las alertas?\n\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
            
        if reply == QMessageBox.Yes:
            self.alert_system.clear_alerts()
            self.load_alerts()
            QMessageBox.information(
                self,
                "Éxito",
                "Todas las alertas han sido eliminadas."
            )