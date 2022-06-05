from django.db import models
from django.contrib.auth.models import User


class tracker(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)
	category = models.CharField(
		choices=(
			('Anime', 'Anime'),
			('Movie', 'Movie'),
			('Series', 'Series'),
			('Book', 'Book'),
			('Manga', 'Manga'),
			('Webtoon', 'Webtoon'),
			('Other', 'Other')
		),
		default='Other',
		max_length=10
	)
	title = models.CharField(max_length=100, blank=False)
	episode = models.IntegerField(blank=True, null=True)
	chapter = models.IntegerField(blank=True, null=True)
	timestamp = models.TimeField(null=True, blank=True)
	link = models.URLField(null=True, blank=True)

	class Meta:
		verbose_name_plural = "tracker"

	def __str__(self):
		return f'{self.user.username} | {self.title}'


class todo(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)
	title = models.CharField(max_length=200, blank=False)
	priority = models.CharField(
		choices=(
			('High', 'High'),
			('Medium', 'Medium'),
			('Low', 'Low')
		),
		default='Low',
		max_length=10
	)
	description = models.TextField(null=True, blank=True)
	due_date = models.DateField(null=True, blank=True)
	due_time = models.TimeField(null=True, blank=True)
	notes = models.TextField(null=True, blank=True)
	reminder = models.DateTimeField(null=True, blank=True)
	isCompleted = models.BooleanField(default=False)
	completed_on = models.DateTimeField(null=True, blank=True)

	class Meta:
		verbose_name_plural = "todo"

	def __str__(self):
		return f'{self.user.username} | {self.title}'
