import logging
import sys
import threading
import traceback
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from app.src.utils.settings import get_settings
import os


settings = get_settings()


class Logger:
    """Simple centralized logger for all CureForge AI components."""

    _loggers = {}
    _log_dir = None
    _exception_hooks_installed = False

    class _SingleLineFormatter(logging.Formatter):
        """Formatter that strips traceback text from standard logs."""

        def format(self, record):
            original_exc_info = record.exc_info
            original_exc_text = record.exc_text
            original_stack_info = record.stack_info
            try:
                record.exc_info = None
                record.exc_text = None
                record.stack_info = None
                return super().format(record)
            finally:
                record.exc_info = original_exc_info
                record.exc_text = original_exc_text
                record.stack_info = original_stack_info

    @classmethod
    def _get_log_dir(cls) -> Path:
        """Get or create the logs directory at project root."""
        if cls._log_dir is None:
            cls._log_dir = Path(settings.default_paths["logs"])
            os.makedirs(cls._log_dir, exist_ok=True)
        return cls._log_dir

    @classmethod
    def _get_log_file(cls) -> Path:
        """Get today's log file path."""
        log_dir = cls._get_log_dir()
        today = datetime.now().strftime("%Y-%m-%d")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir / f"{today}.log"

    @classmethod
    def _get_error_log_file(cls) -> Path:
        """Get today's error traceback log file path."""
        log_dir = cls._get_log_dir()
        today = datetime.now().strftime("%Y-%m-%d")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir / f"{today}-error.log"

    @classmethod
    def _append_traceback(cls, error_id: str, trace_text: str) -> None:
        """Append full traceback to today's dedicated error log."""
        error_file = cls._get_error_log_file()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(error_file, "a", encoding="utf-8") as stream:
            stream.write(f"[{timestamp}] error_id={error_id}\n")
            stream.write(trace_text)
            if not trace_text.endswith("\n"):
                stream.write("\n")
            stream.write("\n")

    @classmethod
    def _install_exception_hooks(cls) -> None:
        """Install concise global exception hooks once per process."""
        if cls._exception_hooks_installed:
            return

        def _handle_uncaught(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                return

            error_id = uuid4().hex[:12]
            trace_text = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
            cls._append_traceback(error_id, trace_text)
            root_logger = cls.get_logger("uncaught")
            root_logger.error(
                "Unhandled exception: %s [error_id=%s] (full traceback in %s)",
                exc_value,
                error_id,
                cls._get_error_log_file().name,
            )

        def _handle_thread_exception(args: threading.ExceptHookArgs):
            if issubclass(args.exc_type, KeyboardInterrupt):
                return

            error_id = uuid4().hex[:12]
            trace_text = "".join(
                traceback.format_exception(
                    args.exc_type,
                    args.exc_value,
                    args.exc_traceback,
                )
            )
            cls._append_traceback(error_id, trace_text)
            root_logger = cls.get_logger("uncaught")
            thread_name = args.thread.name if args.thread else "unknown"
            root_logger.error(
                "Unhandled thread exception in %s: %s [error_id=%s] (full traceback in %s)",
                thread_name,
                args.exc_value,
                error_id,
                cls._get_error_log_file().name,
            )

        sys.excepthook = _handle_uncaught
        threading.excepthook = _handle_thread_exception
        cls._exception_hooks_installed = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger with the specified name.

        Args:
            name: Logger name (typically module name)

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        logger.handlers.clear()

        # timestamp - [LEVEL] => message
        formatter = cls._SingleLineFormatter(
            fmt="%(asctime)s - [%(levelname)s] => %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        try:
            log_file = cls._get_log_file()
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler: {e}")

        logger.propagate = False

        cls._loggers[name] = logger
        cls._install_exception_hooks()
        return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (use __name__ for automatic module naming)

    Returns:
        Configured logger instance
    """
    return Logger.get_logger(name)
