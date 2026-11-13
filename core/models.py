import math
import re
from django.conf import settings
from django.db import models
from django.urls import reverse


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True, allow_unicode=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class News(models.Model):
    CATEGORY_CHOICES = [
        ('news', 'Новости'),
        ('articles', 'Статьи'),
        ('reviews', 'Обзоры'),
    ]
    TOPIC_CHOICES = [
        ('other', 'Другое'),
        ('iphone-17', 'iPhone 17'),
        ('iphone-18', 'iPhone 18'),
        ('iphone-duo', 'iPhone Duo'),
        ('ios-27', 'iOS 27'),
    ]
    STATUS_CHOICES = [('draft', 'Черновик'), ('published', 'Опубликовано')]

    image = models.ImageField(upload_to='newsphotos/', blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=500)
    content = models.TextField(blank=True, default='')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='news')
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='other')
    source_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='nexora_posts')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='published', db_index=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Публикация'
        verbose_name_plural = 'Публикации'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.pk])

    @property
    def score(self):
        return self.likes_count - self.dislikes_count


    @property
    def author_badge(self):
        if not self.author_id:
            return ''
        if self.author.is_superuser:
            return 'Главный администратор'
        if self.author.groups.filter(name='Administrators').exists():
            return 'Администратор'
        if self.author.groups.filter(name='Moderators').exists():
            return 'Модератор'
        return ''

    @property
    def reading_minutes(self):
        words = re.findall(r'\w+', self.content or self.description)
        return max(1, math.ceil(len(words) / 200))


class PostReaction(models.Model):
    LIKE = 1
    DISLIKE = -1
    CHOICES = [(LIKE, 'Нравится'), (DISLIKE, 'Не нравится')]
    post = models.ForeignKey(News, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_reactions')
    value = models.SmallIntegerField(choices=CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='one_reaction_per_reader'),
            models.CheckConstraint(condition=models.Q(value__in=[-1, 1]), name='reaction_is_vote'),
        ]


class PostView(models.Model):
    post = models.ForeignKey(News, on_delete=models.CASCADE, related_name='visits')
    visitor_key = models.CharField(max_length=32)
    viewed_on = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'visitor_key', 'viewed_on'], name='one_post_view_per_day'),
        ]


class NexoraAvatar(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nexora_avatar')
    image = models.ImageField(upload_to='avatars/')
