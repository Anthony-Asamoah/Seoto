from django.contrib.admin.sites import site
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase

from domains.apps.rhymes.models import Rhyme


class OwnerScopedAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', is_staff=True)
        cls.bob = User.objects.create_user('bob', is_staff=True)
        for user in (cls.alice, cls.bob):
            Rhyme.objects.create(user=user, rhyme='cat', text='cat hat', word_count=2)

    def queryset_for(self, user):
        user = User.objects.get(pk=user.pk)
        request = RequestFactory().get('/admin/')
        request.user = user
        return site._registry[Rhyme].get_queryset(request)

    def test_scoped_to_own_records_without_view_all(self):
        self.assertEqual([r.user for r in self.queryset_for(self.alice)], [self.alice])

    def test_view_all_shows_everyone(self):
        self.alice.user_permissions.add(Permission.objects.get(codename='view_all_rhyme'))
        self.assertEqual(self.queryset_for(self.alice).count(), 2)

    def test_superuser_sees_everyone(self):
        root = User.objects.create_superuser('root', password='x')
        self.assertEqual(self.queryset_for(root).count(), 2)
