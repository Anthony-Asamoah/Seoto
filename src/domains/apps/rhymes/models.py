from django.contrib.auth.models import User
from django.db import models

from infrastructure.core.model_validators import Validators


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

    def generate_file_content(self):
        """Generate friendly, readable file content as a string without writing to disk."""
        content = []

        # Friendly title
        content.append(f'Rhymes for "{self.rhyme.lower()}"')
        content.append('')
        content.append(f'Found {self.word_count} word(s) that rhyme.')
        content.append(f'Saved on {self.timestamp.strftime("%B %d, %Y")}.')
        content.append('')
        content.append('-' * 40)
        content.append('')

        # Words list
        content.append(self.text)
        content.append('')

        # Footer
        content.append('-' * 40)
        content.append('Made with Seoto · seoto.com')

        return '\n'.join(content)
