from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QCheckBox, QMessageBox, QListWidgetItem, QFrame,
                            QGraphicsDropShadowEffect, QScrollArea, QWidget, QGridLayout)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPixmap, QCursor
from loguru import logger
import time
from pathlib import Path
import cv2
from datetime import datetime

class AlertDetailDialog(QDialog):
    """Ventana de ficha policial estilo ID Card - Sin scroll"""
    
    def __init__(self, alert_event, database, parent=None):
        super().__init__(parent)
        self.alert_event = alert_event
        self.database = database
        self.face_data = None
        
        self.setWindowTitle(f"Ficha - {alert_event.face_name}")
        self.setModal(True)
        self.setFixedSize(1100, 750)  # Tamaño fijo, sin scroll
        
        # Cargar datos de la base de datos
        self.load_face_data()
        
        self.setup_style()
        self.init_ui()
        
    def load_face_data(self):
        """Cargar datos completos desde la base de datos"""
        try:
            known_faces = self.database.get_known_faces()
            logger.info(f"Searching for: '{self.alert_event.face_name}' in {len(known_faces)} known faces")
            
            alert_name_normalized = self.alert_event.face_name.lower().strip()
            
            for face in known_faces:
                name = face['name'].lower().strip()
                lastname = face.get('lastname', '').lower().strip()
                full_name = f"{name} {lastname}".strip()
                
                if (alert_name_normalized == name or 
                    alert_name_normalized == full_name or
                    alert_name_normalized == f"{name}{lastname}" or
                    name in alert_name_normalized or
                    alert_name_normalized in full_name):
                    
                    self.face_data = face
                    logger.info(f"✅ Found face data: {face['name']} {face.get('lastname', '')} - Cedula: {face.get('cedula', 'N/A')}")
                    break
            
            if not self.face_data:
                logger.warning(f"❌ No database record found for: '{self.alert_event.face_name}'")
                available_names = [f"{f['name']} {f.get('lastname', '')}" for f in known_faces[:5]]
                logger.debug(f"Available names in DB: {available_names}")
                
        except Exception as e:
            logger.error(f"Error loading face data: {e}", exc_info=True)
    
    def setup_style(self):
        """Estilo tipo ficha policial"""
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
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
        """)
    
    def init_ui(self):
        """Crear interfaz tipo ficha policial"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # HEADER - Título de ficha
        header = self.create_header()
        layout.addWidget(header)
        
        # GRID PRINCIPAL - 2 columnas
        content_grid = QGridLayout()
        content_grid.setSpacing(16)
        
        # COLUMNA IZQUIERDA - Foto y datos básicos
        left_card = self.create_left_card()
        content_grid.addWidget(left_card, 0, 0)
        
        # COLUMNA DERECHA - Información detallada
        right_card = self.create_right_card()
        content_grid.addWidget(right_card, 0, 1)
        
        layout.addLayout(content_grid)
        
        # FOOTER - Botón cerrar
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        close_btn = QPushButton("CERRAR FICHA")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(200)
        footer_layout.addWidget(close_btn)
        footer_layout.addStretch()
        
        layout.addLayout(footer_layout)
    
    def create_header(self):
        """Header tipo ficha oficial"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 212, 0.4),
                    stop:1 rgba(0, 120, 212, 0.2));
                border: 2px solid rgba(0, 120, 212, 0.6);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 120, 212, 100))
        shadow.setOffset(0, 3)
        header_frame.setGraphicsEffect(shadow)
        
        header_layout = QHBoxLayout(header_frame)
        
        # Título
        title = QLabel("🆔 FICHA DE IDENTIFICACIÓN")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Fecha/Hora de detección
        time_str = datetime.fromtimestamp(self.alert_event.timestamp).strftime("%d/%m/%Y  %H:%M:%S")
        date_label = QLabel(f"📅 {time_str}")
        date_label.setStyleSheet("""
            font-size: 14px;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 600;
        """)
        header_layout.addWidget(date_label)
        
        return header_frame
    
    def create_left_card(self):
        """Tarjeta izquierda - Foto y datos básicos"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        
        # FOTOGRAFÍA
        photo_container = QFrame()
        photo_container.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.4);
                border: 3px solid rgba(0, 120, 212, 0.5);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        photo_layout = QVBoxLayout(photo_container)
        
        photo_label = QLabel("FOTOGRAFÍA")
        photo_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.7);
            letter-spacing: 1px;
        """)
        photo_label.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(photo_label)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(380, 280)
        self.image_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
        """)
        self.load_image()
        photo_layout.addWidget(self.image_label)
        
        card_layout.addWidget(photo_container)
        
        # NOMBRE COMPLETO
        if self.face_data:
            full_name = f"{self.face_data['name'].upper()} {self.face_data.get('lastname', '').upper()}"
        else:
            full_name = self.alert_event.face_name.upper()
        
        name_label = QLabel(full_name)
        name_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #4FC3F7;
            letter-spacing: 1px;
            padding: 12px;
            background-color: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        card_layout.addWidget(name_label)
        
        # CONFIANZA
        confidence_pct = self.alert_event.confidence * 100 if self.alert_event.confidence <= 1 else self.alert_event.confidence
        confidence_color = "#4CAF50" if confidence_pct >= 80 else "#FFC107" if confidence_pct >= 60 else "#F44336"
        
        confidence_label = QLabel(f"🎯 CONFIANZA: {confidence_pct:.1f}%")
        confidence_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {confidence_color};
            background-color: rgba(0, 0, 0, 0.4);
            padding: 10px;
            border-radius: 6px;
            border: 2px solid {confidence_color};
        """)
        confidence_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(confidence_label)
        
        card_layout.addStretch()
        
        return card
    
    def create_right_card(self):
        """Tarjeta derecha - Información detallada"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        
        # DATOS PERSONALES
        personal_section = self.create_section("👤 DATOS PERSONALES")
        card_layout.addWidget(personal_section)
        
        # DATOS BIOMÉTRICOS
        bio_section = self.create_section("🧬 DATOS BIOMÉTRICOS")
        card_layout.addWidget(bio_section)
        
        # INFORMACIÓN LEGAL (solo si existe)
        if self.face_data and (self.face_data.get('crime') or self.face_data.get('case_number')):
            legal_section = self.create_section("⚖️ INFORMACIÓN LEGAL", is_alert=True)
            card_layout.addWidget(legal_section)
        
        # DETECCIÓN
        detection_section = self.create_section("📹 DATOS DE DETECCIÓN")
        card_layout.addWidget(detection_section)
        
        card_layout.addStretch()
        
        return card
    
    def create_section(self, title, is_alert=False):
        """Crear sección de información"""
        section = QFrame()
        
        if is_alert:
            section.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(244, 67, 54, 0.3),
                        stop:1 rgba(244, 67, 54, 0.1));
                    border: 2px solid rgba(244, 67, 54, 0.5);
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
        else:
            section.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
        
        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(8)
        
        # Título de sección
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #64B5F6;
            letter-spacing: 1px;
            margin-bottom: 4px;
        """)
        section_layout.addWidget(title_label)
        
        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(100, 181, 246, 0.3); max-height: 2px;")
        section_layout.addWidget(line)
        
        # Contenido según la sección
        if "PERSONALES" in title:
            self.add_personal_data(section_layout)
        elif "BIOMÉTRICOS" in title:
            self.add_biometric_data(section_layout)
        elif "LEGAL" in title:
            self.add_legal_data(section_layout)
        elif "DETECCIÓN" in title:
            self.add_detection_data(section_layout)
        
        return section
    
    def add_personal_data(self, layout):
        """Agregar datos personales"""
        if self.face_data:
            if self.face_data.get('cedula'):
                self.add_data_row(layout, "Cédula:", self.face_data['cedula'], "📋")
            if self.face_data.get('birth_date'):
                try:
                    birth_date = datetime.strptime(self.face_data['birth_date'], "%Y-%m-%d")
                    formatted_date = birth_date.strftime("%d/%m/%Y")
                    self.add_data_row(layout, "Fecha Nac.:", formatted_date, "📅")
                except:
                    self.add_data_row(layout, "Fecha Nac.:", self.face_data['birth_date'], "📅")
        else:
            no_data = QLabel("⚠️ Sin datos en base de datos")
            no_data.setStyleSheet("color: #FFC107; font-size: 12px; font-style: italic;")
            layout.addWidget(no_data)
    
    def add_biometric_data(self, layout):
        """Agregar datos biométricos"""
        # Edad
        display_age = None
        age_source = ""
        
        if self.face_data and self.face_data.get('age'):
            display_age = self.face_data['age']
            age_source = "(Registrado)"
        elif self.alert_event.age:
            display_age = self.alert_event.age
            age_source = "(Estimado IA)"
        
        if display_age:
            self.add_data_row(layout, "Edad:", f"{display_age} años {age_source}", "👶")
        
        # Género
        if self.alert_event.gender:
            self.add_data_row(layout, "Género:", f"{self.alert_event.gender} (Detectado IA)", "🚻")
    
    def add_legal_data(self, layout):
        """Agregar información legal"""
        if self.face_data:
            if self.face_data.get('crime'):
                crime_label = QLabel(f"🚨 {self.face_data['crime']}")
                crime_label.setStyleSheet("""
                    color: #FF5252;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px;
                    background-color: rgba(255, 82, 82, 0.1);
                    border-radius: 4px;
                """)
                crime_label.setWordWrap(True)
                layout.addWidget(crime_label)
            
            if self.face_data.get('case_number'):
                self.add_data_row(layout, "Expediente:", self.face_data['case_number'], "📁")
    
    def add_detection_data(self, layout):
        """Agregar datos de detección"""
        self.add_data_row(layout, "Cámara:", f"{self.alert_event.camera_name}", "📹")
        self.add_data_row(layout, "ID Cámara:", f"{self.alert_event.camera_id}", "🔢")
    
    def add_data_row(self, layout, label, value, icon=""):
        """Agregar fila de datos"""
        row = QHBoxLayout()
        row.setSpacing(8)
        
        label_widget = QLabel(f"{icon} {label}")
        label_widget.setStyleSheet("""
            color: rgba(255, 255, 255, 0.7);
            font-size: 12px;
            font-weight: 600;
            min-width: 100px;
        """)
        row.addWidget(label_widget)
        
        value_widget = QLabel(str(value))
        value_widget.setStyleSheet("""
            color: white;
            font-size: 12px;
            font-weight: 500;
        """)
        value_widget.setWordWrap(True)
        row.addWidget(value_widget, 1)
        
        layout.addLayout(row)
    
    def load_image(self):
        """Cargar imagen de captura"""
        if not self.alert_event.screenshot_path:
            self.image_label.setText("📷\n\nSIN IMAGEN")
            self.image_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.3);
                font-size: 16px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
            """)
            return
        
        screenshot_path = Path(self.alert_event.screenshot_path)
        if not screenshot_path.exists():
            self.image_label.setText("📷\n\nARCHIVO NO ENCONTRADO")
            return
        
        try:
            image = cv2.imread(str(screenshot_path))
            if image is not None:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = image_rgb.shape
                bytes_per_line = ch * w
                
                from PyQt5.QtGui import QImage
                q_image = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                scaled_pixmap = pixmap.scaled(
                    self.image_label.width() - 10,
                    self.image_label.height() - 10,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            self.image_label.setText("❌\n\nERROR AL CARGAR")


class ClickableAlertItem(QListWidgetItem):
    """Item de lista clickeable personalizado"""
    
    def __init__(self, alert_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_event = alert_event
        self.setFlags(self.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)


class AlertPanel(QDialog):
    def __init__(self, alert_system, database=None):
        super().__init__()
        self.alert_system = alert_system
        self.database = database
        
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
        
        subtitle = QLabel("Haz clic en cualquier alerta para ver la ficha completa")
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
            
            item_text = f"🕒 {time_str}  |  👤 {alert.face_name}  |  📹 {alert.camera_name}  |  🎯 {confidence_pct:.1f}%"
            
            bio_info = []
            if alert.age:
                bio_info.append(f"👶 {alert.age} años")
            if alert.gender:
                bio_info.append(f"🚻 {alert.gender}")
            
            if bio_info:
                item_text += f"\n   {' | '.join(bio_info)}"
            
            item = ClickableAlertItem(alert, item_text)
            
            if confidence_pct >= 80:
                item.setForeground(QColor(76, 175, 80))
            elif confidence_pct >= 60:
                item.setForeground(QColor(255, 193, 7))
            else:
                item.setForeground(QColor(244, 67, 54))
            
            self.alert_list.addItem(item)
            
    def on_alert_clicked(self, item):
        """Handle alert click - show detail dialog"""
        if isinstance(item, ClickableAlertItem):
            try:
                if not self.database:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se puede acceder a la base de datos."
                    )
                    return
                
                detail_dialog = AlertDetailDialog(item.alert_event, self.database, self)
                detail_dialog.exec_()
            except Exception as e:
                logger.error(f"Error showing alert detail: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo mostrar el detalle:\n{str(e)}"
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
            