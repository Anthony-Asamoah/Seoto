import logging
import traceback as tb_module


class DatabaseLogHandler(logging.Handler):
    """Writes ERROR+ log records to the ErrorLog model."""

    def emit(self, record):
        try:
            from home.models import ErrorLog
        except Exception:
            return

        try:
            traceback_str = ''
            if record.exc_info:
                traceback_str = ''.join(tb_module.format_exception(*record.exc_info))

            ErrorLog.objects.create(
                level=record.levelname,
                logger_name=record.name,
                message=record.getMessage(),
                traceback=traceback_str,
                path=getattr(record, 'request_path', ''),
                method=getattr(record, 'request_method', ''),
                user_id=getattr(record, 'request_user_id', None),
            )
        except Exception:
            self.handleError(record)
