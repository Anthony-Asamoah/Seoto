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


APP_LABEL_RENAMES = {
    'company_products': 'website_products',
    'company_faqs': 'website_faqs',
}


def relabel_apps(renames=APP_LABEL_RENAMES, on_progress=None):
    """Move already-migrated apps to a new label: tables, migration history and content types. Idempotent; run before `migrate`."""
    from django.db import connection

    report = on_progress or (lambda message, level='info': None)
    with connection.schema_editor() as editor, connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
        if 'django_migrations' not in tables:
            report('fresh database: nothing to relabel')
            return
        for old, new in renames.items():
            cursor.execute('SELECT COUNT(*) FROM django_migrations WHERE app = %s', [old])
            if not cursor.fetchone()[0]:
                report(f'{old}: nothing to relabel')
                continue
            for table in tables:
                if table.startswith(f'{old}_'):
                    renamed = new + table[len(old):]
                    editor.alter_db_table(None, table, renamed)
                    report(f'  {table} -> {renamed}')
            cursor.execute('UPDATE django_migrations SET app = %s WHERE app = %s', [new, old])
            cursor.execute('UPDATE django_content_type SET app_label = %s WHERE app_label = %s', [new, old])
            report(f'{old} -> {new}', 'success')
