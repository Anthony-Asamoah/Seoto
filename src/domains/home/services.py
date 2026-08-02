import logging
import traceback as tb_module


class ErrorLogService:
    """Service for writing error records to the dashboard ErrorLog."""

    @classmethod
    def log(cls, message, logger_name='', exc_info=None, level='ERROR'):
        """
        Write an entry to ErrorLog and emit via Python logging.

        Args:
            message:     Human-readable error description.
            logger_name: Dotted logger name (e.g. __name__ of the caller).
            exc_info:    sys.exc_info() tuple, or True to capture the current exception.
            level:       'WARNING', 'ERROR', or 'CRITICAL'.
        """
        traceback_str = ''
        if exc_info:
            if exc_info is True:
                import sys
                exc_info = sys.exc_info()
            traceback_str = ''.join(tb_module.format_exception(*exc_info))

        logger = logging.getLogger(logger_name or __name__)
        log_fn = getattr(logger, level.lower(), logger.error)
        log_fn(message, exc_info=exc_info if exc_info else False)

        try:
            from domains.home.models import ErrorLog
            ErrorLog.objects.create(
                level=level.upper(),
                logger_name=logger_name,
                message=message,
                traceback=traceback_str,
            )
        except Exception:
            pass
