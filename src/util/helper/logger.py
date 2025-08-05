import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class CustomFormatter(logging.Formatter):
    """Formateur personnalisé pour les logs avec couleurs et informations structurées."""
    
    COLORS = {
        'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m',
        'ERROR': '\033[31m', 'CRITICAL': '\033[35m', 'RESET': '\033[0m'
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors
    
    def format(self, record):
        record.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record.service = getattr(record, 'service', 'API')
        record.user_id = getattr(record, 'user_id', None)
        record.operation = getattr(record, 'operation', None)
        
        if self.use_colors and getattr(record, 'use_colors', True):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

class APILogger:
    """Logger principal de l'API avec des fonctionnalités avancées."""
    
    def __init__(self, name: str = "API", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configurer les gestionnaires de logs."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CustomFormatter(
            fmt='%(timestamp)s | %(levelname)s | %(service)s | %(name)s | %(message)s'
        ))
        self.logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler(
            log_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'
        )
        file_handler.setFormatter(CustomFormatter(
            fmt='%(timestamp)s | %(levelname)s | %(service)s | %(name)s | %(user_id)s | %(operation)s | %(message)s',
            use_colors=False
        ))
        self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str, **context):
        """Logger avec contexte additionnel."""
        extra = {
            'service': context.get('service', 'API'),
            'user_id': context.get('user_id'),
            'operation': context.get('operation'),
            'use_colors': context.get('use_colors', True)
        }
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def info(self, message: str, **context):
        self.log('INFO', message, **context)
    
    def debug(self, message: str, **context):
        self.log('DEBUG', message, **context)
    
    def warning(self, message: str, **context):
        self.log('WARNING', message, **context)
    
    def error(self, message: str, **context):
        self.log('ERROR', message, **context)
    
    def critical(self, message: str, **context):
        self.log('CRITICAL', message, **context)
    
    def log_operation(self, operation: str, user_id: Optional[int] = None, **details):
        message = f"Operation: {operation} | Details: {details}" if details else f"Operation: {operation}"
        self.info(message, operation=operation, user_id=user_id)
    
    def log_database_operation(self, operation: str, model: str, obj_id: Optional[int] = None, **details):
        message = f"DB {operation} | Modèle: {model}"
        if obj_id:
            message += f" | ID: {obj_id}"
        if details:
            message += f" | Détails: {details}"
        self.info(message, operation=f"DB_{operation}", **details)
    
    def log_performance(self, operation: str, duration: float, **details):
        message = f"Performance | {operation}: {duration:.3f}s"
        if details:
            message += f" | Détails: {details}"
        (self.warning if duration > 1.0 else self.debug)(message, operation="PERFORMANCE")

logger = APILogger()

def log_info(message: str, **context):
    logger.info(message, **context)

def log_error(message: str, **context):
    logger.error(message, **context)

def log_operation(operation: str, user_id: Optional[int] = None, **details):
    logger.log_operation(operation, user_id, **details)

def log_db_operation(operation: str, model: str, obj_id: Optional[int] = None, **details):
    logger.log_database_operation(operation, model, obj_id, **details)