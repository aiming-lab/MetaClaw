"""
Synchronous log handler for Project Orion API
Writes log entries to disk synchronously
"""

import os
from datetime import datetime


class SyncLogHandler:
    """Synchronous log handler that writes directly to disk."""

    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """Create log directory if it doesn't exist."""
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def write_log(self, level, message):
        """Write a log entry synchronously to disk.

        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message content
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}\n"

        # Synchronous write - blocks the calling thread
        with open(self.log_file_path, 'a') as f:
            f.write(log_entry)

    def info(self, message):
        self.write_log("INFO", message)

    def warning(self, message):
        self.write_log("WARNING", message)

    def error(self, message):
        self.write_log("ERROR", message)
