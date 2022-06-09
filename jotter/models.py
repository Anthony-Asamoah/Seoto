from django.db import models
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

priority_choices = (
	('High', 'High'),
	('Medium', 'Medium'),
	('Low', 'Low')
)

tracker_category_choices = (
	('Anime', 'Anime'),
	('Movie', 'Movie'),
	('Series', 'Series'),
	('Book', 'Book'),
	('Manga', 'Manga'),
	('Webtoon', 'Webtoon'),
	('Other', 'Other')
)


class tracker(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)
	category = models.CharField(choices=tracker_category_choices, default='Other', max_length=10)
	title = models.CharField(max_length=100, blank=False)
	episode = models.IntegerField(blank=True, null=True)
	chapter = models.IntegerField(blank=True, null=True)
	timestamp = models.CharField(null=True, blank=True, max_length=20)
	link = models.URLField(null=True, blank=True)
	added_on = models.DateTimeField(default=timezone.now())
	isCompleted = models.BooleanField(default=False)
	completed_on = models.DateTimeField(null=True, blank=True)

	class Meta:
		verbose_name_plural = "tracker"

	def __str__(self):
		return f'{self.user.username} | {self.title}'


class tracker_form(forms.ModelForm):
	class Meta:
		model = tracker
		fields = ['category', 'title', 'episode', 'chapter', 'timestamp', 'link']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'


class todo(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False)
	title = models.CharField(max_length=200, blank=False)
	priority = models.CharField(
		choices=priority_choices,
		default='Low',
		max_length=10
	)
	notes = models.TextField(null=True, blank=True)
	reminder = models.DateTimeField(null=True, blank=True)
	isCompleted = models.BooleanField(default=False)
	completed_on = models.DateTimeField(null=True, blank=True)
	added_on = models.DateTimeField(default=timezone.now())

	class Meta:
		verbose_name_plural = "todo"

	def __str__(self):
		return f'{self.user.username} | {self.title}'


class todo_form(forms.ModelForm):
	class Meta:
		model = todo
		fields = ['title', 'priority', 'notes']
		widgets = {
			'reminder': forms.DateTimeInput(attrs={
				'placeholder': 'Reminder format: YYYY-MM-DD hh-mm-ss'
			}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
