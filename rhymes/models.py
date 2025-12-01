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

    def generate_file_content(self):
        """Generate formatted file content as a string without writing to disk."""
        content = []

        # Header with border
        content.append('=' * 80)
        content.append('RHYME DATABASE'.center(80))
        content.append('Powered by Python & Wine'.center(80))
        content.append('=' * 80)
        content.append('')

        # User and generation info
        content.append(f'Generated for: {self.user.username} ({self.user.email})')
        content.append(f'Date: {self.timestamp.strftime("%B %d, %Y at %I:%M %p")}')
        content.append('-' * 80)
        content.append('')

        # Search query and results
        content.append(f'SEARCH QUERY: "{self.rhyme.lower()}"')
        content.append(f'RESULTS: {self.word_count} word(s) found')
        content.append('')
        content.append('=' * 80)
        content.append('')

        # Words list
        content.append('MATCHING WORDS:')
        content.append('')
        content.append(self.text)
        content.append('')

        # Footer
        content.append('=' * 80)
        content.append('Thank you for using Rhyme Database!'.center(80))
        content.append('Visit us at seoto.com for more tools'.center(80))
        content.append('=' * 80)

        return '\n'.join(content)
