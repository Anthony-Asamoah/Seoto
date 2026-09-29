class OwnerScopedAdminMixin:
    owner_lookup = 'user'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        opts = self.model._meta
        if request.user.has_perm(f'{opts.app_label}.view_all_{opts.model_name}'):
            return qs
        return qs.filter(**{self.owner_lookup: request.user})
