import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from seoto.model_validators import Validators


class Rhyme(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    rhyme = models.CharField(max_length=10, validators=[Validators.str])
    text = models.TextField(validators=[Validators.str])
    word_count = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.rhyme

    class Meta:
        ordering = ['-timestamp']
        db_table = 'rhyme'

    @staticmethod
    def create(rhyme, user, text, word_count):
        queryset = Rhyme.objects.filter(user=user)
        if not queryset.exists():
            return Rhyme.objects.create(rhyme=rhyme, user=user, text=text, word_count=word_count)
        queryset.update(word_count=word_count, rhyme=rhyme, text=text)
        return queryset.first()

    def write_to_file(self, filename='rhymes.txt'):
        path = os.path.join(settings.MEDIA_ROOT, filename)
        with open(path, 'w') as file:
            file.write(f'''{'Rhyme Db'.rjust(60)}\n{'Powered by Python & Wine'.rjust(60)}\n\n''')
            file.write(f'({self.word_count}) Words that rhyme with "{self.rhyme.lower()}"\n\n')
            file.write(f'{self.text}\n')
            file.write((''.center(60, '-')))
