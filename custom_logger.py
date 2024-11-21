import logging
import os
import re
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler

class CustomLogger(object):
    def __init__(self, logger_name='ManagerSpider', log_directory='logs', retention_days=7):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        
        self.log_directory = log_directory
        os.makedirs(self.log_directory, exist_ok=True)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '<font color=\'#%(color)s\'>%(user)s - %(asctime)s - %(levelname)s - %(message)s</font>'
        ))
        self.logger.addHandler(console_handler)
        
        log_file = os.path.join(self.log_directory, 'app.log')
        file_handler = TimedRotatingFileHandler(log_file, when='midnight', backupCount=retention_days)
        file_handler.suffix = "%Y-%m-%d.log"
        file_handler.setFormatter(logging.Formatter('%(user)s - %(asctime)s - %(levelname)s - %(message)s - %(exc_text)s'))
        self.logger.addHandler(file_handler)
        
        self.retention_days = retention_days
        
        self.logger.info("Logging successfully initialized.", extra={'user': 'System', 'color': '3CB371'})
    
    def _clean_old_logs(self):
        retention_period = timedelta(days=self.retention_days)
        now = datetime.now()
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}\.log$')
        
        for file in os.listdir(self.log_directory):
            if not date_pattern.match(file):
                continue
            file_path = os.path.join(self.log_directory, file)
            try:
                file_date_str = file.split('.')[0]
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if now - file_date >= retention_period:
                    os.remove(file_path)
                    self.logger.debug(f'Deleted old log file: {file}', extra={'user': 'System', 'color': '000000'})
            except Exception as e:
                self.logger.error(f'Error deleting log file {file}: {e}', exc_info=True, extra={'user': 'System', 'color': 'FF0000'})
    
    def get_logger(self):
        return self.logger

    def info(self, message, user, color='3CB371'):
        self.logger.info(str(message), extra={'user': user, 'color': color})
    
    def error(self, message, user, color='FF0000'):
        self.logger.error(str(message), extra={'user': user, 'color': color})
    
    def warning(self, message, user, color='FF8C00'):
        self.logger.warning(str(message), extra={'user': user, 'color': color})
    
    def debug(self, message, user, color='000000'):
        self.logger.debug(str(message), extra={'user': user, 'color': color})
