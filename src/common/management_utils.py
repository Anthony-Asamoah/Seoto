def command_progress(command):
    """Adapt a BaseCommand's stdout to the `on_progress(message, level)` callback services take."""
    styles = {
        'success': command.style.SUCCESS,
        'warning': command.style.WARNING,
        'error': command.style.ERROR,
    }

    def on_progress(message, level='info'):
        style = styles.get(level)
        command.stdout.write(style(message) if style else message)

    return on_progress
