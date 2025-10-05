from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QMessageBox, QHeaderView, QFrame, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from loguru import logger
from typing import Optional

class UserManagementDialog(QDialog):
    def __init__(self, database, auth_manager, parent=None):
        super().__init__(parent)
        self.database = database
        self.auth_manager = auth_manager
        
        self.setWindowTitle("User Management")
        self.setGeometry(200, 100, 1000, 600)
        self.setMinimumSize(900, 500)
        
        self.setup_style()
        self.init_ui()
        self.load_users()
        
    def setup_style(self):
        """Apply modern styling"""
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
            QLineEdit, QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
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
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 212, 1);
            }
            QPushButton#deleteButton {
                background-color: rgba(220, 53, 69, 0.8);
            }
            QPushButton#deleteButton:hover {
                background-color: rgba(220, 53, 69, 1);
            }
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                gridline-color: rgba(255, 255, 255, 0.1);
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.3);
            }
            QHeaderView::section {
                background-color: rgba(0, 120, 212, 0.5);
                color: white;
                padding: 8px;
                border: none;
                font-weight: 600;
            }
            QGroupBox {
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("User Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        # User form
        form_group = QGroupBox("Add/Edit User")
        form_layout = QVBoxLayout(form_group)
        form_layout.setSpacing(12)
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)
        
        # Email
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        email_layout.addWidget(self.email_input)
        form_layout.addLayout(email_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Minimum 8 characters")
        password_layout.addWidget(self.password_input)
        form_layout.addLayout(password_layout)
        
        # Role
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["viewer", "operator", "admin"])
        role_layout.addWidget(self.role_combo)
        form_layout.addLayout(role_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add User")
        self.add_btn.clicked.connect(self.add_user)
        button_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("Update User")
        self.update_btn.clicked.connect(self.update_user)
        self.update_btn.setEnabled(False)
        button_layout.addWidget(self.update_btn)
        
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        form_layout.addLayout(button_layout)
        
        layout.addWidget(form_group)
        
        # Users table
        table_label = QLabel("Existing Users")
        table_label.setStyleSheet("font-size: 16px; font-weight: 600; color: white;")
        layout.addWidget(table_label)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Username", "Email", "Role", "Status", "Last Login"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SingleSelection)
        self.users_table.itemSelectionChanged.connect(self.on_user_selected)
        layout.addWidget(self.users_table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_users)
        action_layout.addWidget(self.refresh_btn)
        
        self.toggle_status_btn = QPushButton("Enable/Disable")
        self.toggle_status_btn.clicked.connect(self.toggle_user_status)
        self.toggle_status_btn.setEnabled(False)
        action_layout.addWidget(self.toggle_status_btn)
        
        self.delete_btn = QPushButton("Delete User")
        self.delete_btn.setObjectName("deleteButton")
        self.delete_btn.clicked.connect(self.delete_user)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)
        
        action_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        action_layout.addWidget(self.close_btn)
        
        layout.addLayout(action_layout)
        
    def load_users(self):
        """Load all users into table"""
        try:
            users = self.database.get_all_users()
            self.users_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
                self.users_table.setItem(row, 1, QTableWidgetItem(user['username']))
                self.users_table.setItem(row, 2, QTableWidgetItem(user['email']))
                self.users_table.setItem(row, 3, QTableWidgetItem(user['role']))
                
                # Status with color
                status_item = QTableWidgetItem("Active" if user['is_active'] else "Disabled")
                if user['is_active']:
                    status_item.setForeground(QColor(0, 200, 0))
                else:
                    status_item.setForeground(QColor(255, 100, 100))
                self.users_table.setItem(row, 4, status_item)
                
                # Last login
                if user['last_login']:
                    from datetime import datetime
                    last_login = datetime.fromtimestamp(user['last_login']).strftime("%Y-%m-%d %H:%M")
                else:
                    last_login = "Never"
                self.users_table.setItem(row, 5, QTableWidgetItem(last_login))
                
                # Make ID column read-only
                self.users_table.item(row, 0).setFlags(Qt.ItemIsEnabled)
                
            logger.info(f"Loaded {len(users)} users")
            
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")
    
    def on_user_selected(self):
        """Handle user selection"""
        selected_rows = self.users_table.selectedItems()
        if not selected_rows:
            self.update_btn.setEnabled(False)
            self.toggle_status_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return
        
        # Enable buttons
        self.update_btn.setEnabled(True)
        self.toggle_status_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
        # Load user data into form
        row = self.users_table.currentRow()
        self.username_input.setText(self.users_table.item(row, 1).text())
        self.email_input.setText(self.users_table.item(row, 2).text())
        self.password_input.clear()
        self.password_input.setPlaceholderText("Leave empty to keep current password")
        
        role = self.users_table.item(row, 3).text()
        index = self.role_combo.findText(role)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
    
    def add_user(self):
        """Add new user"""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        role = self.role_combo.currentText()
        
        # Validate
        if not username or not email or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in all fields")
            return
        
        if len(password) < 8:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters")
            return
        
        # Check permission
        if not self.auth_manager.has_permission('admin'):
            QMessageBox.warning(self, "Permission Denied", "Only admins can create users")
            return
        
        try:
            # Hash password
            password_hash = self.auth_manager.hash_password(password)
            
            # Create user
            current_user = self.auth_manager.get_current_user()
            user_id = self.database.create_user(
                username, email, password_hash, role,
                created_by=current_user.id if current_user else None
            )
            
            if user_id:
                QMessageBox.information(self, "Success", f"User '{username}' created successfully")
                self.clear_form()
                self.load_users()
            else:
                QMessageBox.warning(self, "Error", "Username or email already exists")
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create user: {str(e)}")
    
    def update_user(self):
        """Update selected user"""
        row = self.users_table.currentRow()
        if row < 0:
            return
        
        user_id = int(self.users_table.item(row, 0).text())
        email = self.email_input.text().strip()
        role = self.role_combo.currentText()
        password = self.password_input.text()
        
        # Check permission
        if not self.auth_manager.has_permission('admin'):
            QMessageBox.warning(self, "Permission Denied", "Only admins can update users")
            return
        
        try:
            # Update email and role
            self.database.update_user(user_id, email=email, role=role)
            
            # Update password if provided
            if password:
                if len(password) < 8:
                    QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters")
                    return
                password_hash = self.auth_manager.hash_password(password)
                self.database.update_user_password(user_id, password_hash)
            
            QMessageBox.information(self, "Success", "User updated successfully")
            self.clear_form()
            self.load_users()
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update user: {str(e)}")
    
    def toggle_user_status(self):
        """Enable/disable selected user"""
        row = self.users_table.currentRow()
        if row < 0:
            return
        
        user_id = int(self.users_table.item(row, 0).text())
        username = self.users_table.item(row, 1).text()
        current_status = self.users_table.item(row, 4).text() == "Active"
        
        # Check permission
        if not self.auth_manager.has_permission('admin'):
            QMessageBox.warning(self, "Permission Denied", "Only admins can change user status")
            return
        
        # Prevent disabling self
        current_user = self.auth_manager.get_current_user()
        if current_user and current_user.id == user_id:
            QMessageBox.warning(self, "Error", "You cannot disable your own account")
            return
        
        try:
            new_status = not current_status
            self.database.update_user(user_id, is_active=new_status)
            
            status_text = "enabled" if new_status else "disabled"
            QMessageBox.information(self, "Success", f"User '{username}' {status_text}")
            self.load_users()
            
        except Exception as e:
            logger.error(f"Error toggling user status: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change status: {str(e)}")
    
    def delete_user(self):
        """Delete selected user"""
        row = self.users_table.currentRow()
        if row < 0:
            return
        
        user_id = int(self.users_table.item(row, 0).text())
        username = self.users_table.item(row, 1).text()
        
        # Check permission
        if not self.auth_manager.has_permission('admin'):
            QMessageBox.warning(self, "Permission Denied", "Only admins can delete users")
            return
        
        # Prevent deleting self
        current_user = self.auth_manager.get_current_user()
        if current_user and current_user.id == user_id:
            QMessageBox.warning(self, "Error", "You cannot delete your own account")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete user '{username}'?\n\n"
            "This will deactivate the account.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.database.delete_user(user_id):
                    QMessageBox.information(self, "Success", f"User '{username}' deleted")
                    self.clear_form()
                    self.load_users()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete user")
                    
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")
    
    def clear_form(self):
        """Clear input form"""
        self.username_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.password_input.setPlaceholderText("Minimum 8 characters")
        self.role_combo.setCurrentIndex(0)
        self.users_table.clearSelection()
        self.update_btn.setEnabled(False)
        self.toggle_status_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)