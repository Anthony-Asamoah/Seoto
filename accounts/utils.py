def user_directory_file_path(instance, filename, prefix: str = None, suffix: str = None):
    path = f"{instance.user.username}/{filename}"
    if prefix:
        if not prefix.endswith('/'):
            prefix = '/' + prefix
            path = prefix + path
    if suffix:
        if not suffix.startswith('/'):
            suffix = '/' + suffix
            path = path + suffix
    return path
