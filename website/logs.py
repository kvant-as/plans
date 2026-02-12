import os
import sys
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
import traceback

class logs(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        if hasattr(record, 'extra'):
            log_data.update(record.extra)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(app):
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "py-app.log")
    
    log_level = app.config.get('LOG_LEVEL', 'DEBUG').upper()
    
    json_formatter = logs()

    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(json_formatter)
    file_handler.set_name('json_file_handler')
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(console_formatter)
    console_handler.set_name('console_handler')
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    app.logger.handlers.clear()
    app.logger.propagate = True

    app.logger.info("=" * 60)
    app.logger.info(f"Launch time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app.logger.info(f"Logging level: {log_level}")
    app.logger.info(f"Debug mode: {app.config.get('DEBUG', False)}")
    app.logger.info(f"Logs are recorded in: {log_file}")
    app.logger.info("=" * 60)
    
def log_with_extra(logger, level, message, **extra_fields):
    if hasattr(logger, level.lower()):
        log_method = getattr(logger, level.lower())
        extra = {}
        extra.update(extra_fields)
        
        log_method(message, extra={'extra': extra})
    else:
        logger.info(message, extra={'extra': extra_fields})