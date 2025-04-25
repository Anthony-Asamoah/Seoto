# blog/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class PostTags(models.Model):
    label = models.CharField(max_length=200)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name_plural = "Post Tags"


class PostReadGroup(models.Model):
    label = models.CharField(max_length=200)
    users = models.ManyToManyField(User, blank=True, related_name="post_read_groups")
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.label


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    tags = models.ManyToManyField(PostTags, blank=True)

    allowed_groups = models.ManyToManyField(PostReadGroup, blank=True, related_name="allowed_posts")
    allowed_users = models.ManyToManyField(User, blank=True, related_name="allowed_posts")

    class Meta:
        unique_together = ("title", "author", "is_public")

    def __str__(self):
        return self.title