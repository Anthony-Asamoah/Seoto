from whitenoise.storage import CompressedManifestStaticFilesStorage


class AdminSafeStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Manifest storage that tolerates jazzmin's one non-file `{% static %}` call.

    jazzmin's admin/base.html resolves `{% static 'vendor/bootswatch' %}` — a directory,
    used as a base URL by the client-side theme chooser. Directories never get a manifest
    entry, so strict lookup raises on every admin page once DEBUG is off. Everything
    outside this allowlist stays strict, so genuinely missing files still fail loudly.
    """

    tolerated_missing = frozenset({'vendor/bootswatch'})

    def stored_name(self, name):
        if name in self.tolerated_missing:
            return name
        return super().stored_name(name)
