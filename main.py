

import sys
import yaml
from pathlib import Path
from loguru import logger
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

from ui.main_window import MainWindow
from ui.login_window import LoginWindow
from core.auth_manager import AuthManager

def load_config(config_path: str) -> dict:
    """
    Load application configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Ensure required directories exist
        Path(config['app']['screenshot_dir']).mkdir(parents=True, exist_ok=True)
        Path(config['app']['known_faces_dir']).mkdir(parents=True, exist_ok=True)
        Path(config['app']['log_dir']).mkdir(parents=True, exist_ok=True)
        
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

def setup_logging(log_dir: str):
    """
    Initialize application logging with loguru.
    
    Args:
        log_dir: Directory for log files
    """
    logger.add(
        f"{log_dir}/app.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO"
    )
    logger.add(
        f"{log_dir}/error.log",
        rotation="10 MB",
        retention="30 days",
        level="ERROR"
    )
    logger.add(
        f"{log_dir}/security.log",
        rotation="10 MB",
        retention="90 days",
        level="WARNING",
        filter=lambda record: "auth" in record["extra"] or "security" in record["extra"]
    )

def show_splash_screen(config: dict) -> QSplashScreen:
    """Create and display splash screen with logo"""
    try:
        logo_path = config.get('app', {}).get('logo', 'assets/logo.png')
        
        if not Path(logo_path).exists():
            raise FileNotFoundError(f"Logo file not found: {logo_path}")
        
        splash_pix = QPixmap(logo_path)
        if splash_pix.isNull():
            raise ValueError(f"Invalid logo image: {logo_path}")
            
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())

        splash.showMessage(
            "Initializing Face Tracker...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )
        QApplication.processEvents()
        
        return splash
        
    except Exception as e:
        logger.warning(f"Error loading splash screen: {e}")
        return QSplashScreen(QPixmap(800, 400))

def main():
    """
    Main entry point with authentication.
    
    Flow:
    1. Load configuration and setup logging
    2. Initialize database and auth manager
    3. Show login window
    4. On successful login, show main application
    5. Maintain user session throughout
    """
    try:
        # Load configuration
        config = load_config('config/config.yaml')
        
        # Setup logging
        setup_logging(config['app']['log_dir'])
        logger.info("=" * 60)
        logger.info("Application starting...")
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(config['app']['name'])
        app.setApplicationVersion(config['app']['version'])
        
        # Show splash screen
        splash = show_splash_screen(config)
        splash.show()
        app.processEvents()
        
        # Initialize database (creates tables if needed)
        from core.database import FaceDatabase
        database = FaceDatabase(config['app']['database_path'])
        
        # Initialize authentication manager
        auth_manager = AuthManager(database)
        
        splash.showMessage(
            "Loading authentication system...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )
        app.processEvents()
        
        # Show login window
        splash.finish(None)
        login_window = LoginWindow(auth_manager, config)
        
        if login_window.exec_() != LoginWindow.Accepted:
            logger.info("Login cancelled by user")
            return 0
        
        # Get authenticated user
        current_user = auth_manager.get_current_user()
        if not current_user:
            logger.error("No authenticated user after login")
            QMessageBox.critical(
                None, 
                "Authentication Error", 
                "Failed to establish user session"
            )
            return 1
        
        logger.info(f"User '{current_user.username}' (role: {current_user.role}) logged in successfully")
        
        # Show splash again for main app initialization
        splash.show()
        splash.showMessage(
            "Loading AI Models...",
            Qt.AlignBottom | Qt.AlignCenter,
            Qt.white
        )
        app.processEvents()
        
        # Initialize main window with authenticated user
        window = MainWindow(config, auth_manager, database)
        
        # Setup final close timer
        def show_main_window():
            splash.finish(window)
            window.show()
            logger.info("Main application window shown")
        
        QTimer.singleShot(2000, show_main_window)
        
        # Handle application close
        def on_close():
            try:
                logger.info(f"User '{current_user.username}' logging out")
                window.camera_manager.stop_all_cameras()
                window.alert_system.shutdown()
                auth_manager.logout()
                logger.info("Application shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
            finally:
                app.quit()
        
        app.aboutToQuit.connect(on_close)
        
        # Start event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        QMessageBox.critical(
            None,
            "Critical Error",
            f"Application failed to start:\n\n{str(e)}\n\nCheck logs for details."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()