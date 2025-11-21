from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QCheckBox, QFrame, QGraphicsDropShadowEffect,
                            QMessageBox, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QKeyEvent
from loguru import logger

class LoginWindow(QDialog):
    login_successful = pyqtSignal(object)  # Emits User object on successful login
    
    def __init__(self, auth_manager, config):
        super().__init__()
        self.auth_manager = auth_manager
        self.config = config
        self.setWindowTitle("Face Recognition System - Login")
        self.setFixedSize(450, 680)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setup_ui()
        self.setup_animations()
        
    def setup_ui(self):
        """Setup modern login UI"""
        # Main container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Card container
        card = QFrame()
        card.setObjectName("loginCard")
        card.setStyleSheet("""
            QFrame#loginCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 30, 45, 0.95),
                    stop:1 rgba(22, 33, 62, 0.95));
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(12)
        
        # Logo
        logo_label = QLabel()
        logo_path = self.config['app'].get('logo', 'assets/logo.png')
        
        try:
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                raise FileNotFoundError
        except:
            logo_label.setText("🔐")
            logo_label.setStyleSheet("font-size: 64px;")
        
        logo_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(logo_label)
        
        # Title
        title = QLabel("Face Recognition System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-top: 10px;
        """)
        card_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Please sign in to continue")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 20px;
        """)
        card_layout.addWidget(subtitle)
        
        # Username field
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 13px; font-weight: 500;")
        card_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(0, 120, 212, 0.8);
            }
        """)
        card_layout.addWidget(self.username_input)
        
        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 13px; font-weight: 500; margin-top: 10px;")
        card_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.username_input.setMinimumHeight(42)
        self.password_input.setMinimumHeight(42)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(0, 120, 212, 0.8);
            }
        """)
        card_layout.addWidget(self.password_input)
        
        # Connect Enter key navigation
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.login)
        
        # Remember me & Forgot password
        options_layout = QHBoxLayout()
        
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
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
        """)
        options_layout.addWidget(self.remember_checkbox)
        options_layout.addStretch()
        
        forgot_btn = QPushButton("Forgot password?")
        forgot_btn.setFlat(True)
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.setStyleSheet("""
            QPushButton {
                color: #0078d4;
                background-color: transparent;
                border: none;
                font-size: 12px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1e90ff;
            }
        """)
        forgot_btn.clicked.connect(self.forgot_password)
        options_layout.addWidget(forgot_btn)
        
        card_layout.addLayout(options_layout)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            color: #ff6b6b;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(255, 107, 107, 0.1);
            border-radius: 6px;
        """)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)
        
        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e90ff;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: rgba(0, 120, 212, 0.3);
            }
        """)
        self.login_btn.clicked.connect(self.login)
        card_layout.addWidget(self.login_btn)
        
        # Close button
        close_btn = QPushButton("Exit")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
            }
        """)
        close_btn.clicked.connect(self.reject)
        card_layout.addWidget(close_btn)
        
        # Version info
        version_label = QLabel(f"Version {self.config['app']['version']}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4);
            font-size: 11px;
            margin-top: 10px;
        """)
        card_layout.addWidget(version_label)
        
        main_layout.addWidget(card)
        
        # Focus on username
        self.username_input.setFocus()
        
    def setup_animations(self):
        """Setup entrance animation"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
    
    def login(self):
        """Handle login attempt"""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Validate inputs
        if not username or not password:
            self.show_error("Please enter both username and password")
            return

        # Disable button during login
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")

        try:
            # Attempt login
            success, message, user = self.auth_manager.login(username, password)

            if success:
                logger.info(f"Login successful for user: {username}")
                self.login_successful.emit(user)
                self.accept()
                return
            else:
                logger.warning(f"Login failed for user: {username} - {message}")
                # show_error maneja la animación y el label
                self.show_error(message)
                # limpiar password y preparar reintento
                self.password_input.clear()
                self.password_input.setFocus()

        except Exception as e:
            logger.exception(f"Unexpected error during login: {e}")
            # Mostrar un mensaje de error genérico al usuario
            try:
                self.show_error("Unexpected error occurred. Check logs.")
            except Exception:
                pass
            
        finally:
            # Si no se aceptó (login fallido) re-habilitar botones para reintento
            if not getattr(self, "_accepted", False):
                try:
                    self.login_btn.setEnabled(True)
                    self.login_btn.setText("Sign In")
                except Exception:
                    pass

    
    def show_error(self, message: str):
        """Display error message"""
        self.error_label.setText(message)
        self.error_label.show()
        
        # Shake animation
        original_pos = self.pos()
        shake_animation = QPropertyAnimation(self, b"pos")
        shake_animation.setDuration(250)
        shake_animation.setLoopCount(1)
        
        
        
        positions = [
            QPoint(original_pos.x() - 8, original_pos.y()),
            QPoint(original_pos.x() + 8, original_pos.y()),
        ]
        
        for i, pos in enumerate(positions):
            shake_animation.setKeyValueAt(i / len(positions), pos)
        
        offset = 8
        shake_animation.setKeyValueAt(0.0, original_pos)
        shake_animation.setKeyValueAt(0.10, QPoint(original_pos.x() - offset, original_pos.y()))
        shake_animation.setKeyValueAt(0.30, QPoint(original_pos.x() + offset, original_pos.y()))
        shake_animation.setKeyValueAt(0.50, QPoint(original_pos.x() - offset, original_pos.y()))
        shake_animation.setKeyValueAt(0.70, QPoint(original_pos.x() + offset, original_pos.y()))
        shake_animation.setKeyValueAt(1.0, original_pos)
        
        # Guardar referencia para que no sea recolectada
        self._shake_animation = shake_animation

    # Iniciar la animación en un try/except para evitar fallos de render en Windows
        try:
            self._shake_animation.start()
        except Exception as e:
            logger.warning(f"Shake animation failed: {e}")
        
        
    def forgot_password(self):
        """Handle forgot password"""
        QMessageBox.information(
            self,
            "Forgot Password",
            "Please contact your system administrator to reset your password.\n\n"
            "Default admin credentials:\n"
            "Username: admin\n"
            "Password: admin123",
            QMessageBox.Ok
        )
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)