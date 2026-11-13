from django.test import TestCase
from django.urls import reverse

from .models import News


class NexoraViewsTests(TestCase):
    def setUp(self):
        self.article = News.objects.create(
            name='Тестовая статья iPhone 17',
            description='Материал для проверки',
            content='Внутри упомянуто слово ProMotion',
            category='articles',
            topic='iphone-17',
        )
        self.review = News.objects.create(
            name='Обзор iPhone Duo',
            description='Материал про складной смартфон',
            category='reviews',
            topic='iphone-duo',
        )

    def test_home_renders(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.name)

    def test_search_by_title(self):
        response = self.client.get(reverse('index'), {'q': 'Duo'})
        self.assertContains(response, self.review.name)
        self.assertNotContains(response, self.article.name)

    def test_search_by_content(self):
        response = self.client.get(reverse('index'), {'q': 'ProMotion'})
        self.assertContains(response, self.article.name)

    def test_category_filter(self):
        response = self.client.get(reverse('category_posts', args=['reviews']))
        self.assertContains(response, self.review.name)
        self.assertNotContains(response, self.article.name)

    def test_topic_filter(self):
        response = self.client.get(reverse('topic_posts', args=['iphone-17']))
        self.assertContains(response, self.article.name)
        self.assertNotContains(response, self.review.name)

    def test_post_detail(self):
        response = self.client.get(reverse('post_detail', args=[self.article.pk]))
        self.assertContains(response, 'ProMotion')

    def test_invalid_category_is_404(self):
        response = self.client.get(reverse('category_posts', args=['bad']))
        self.assertEqual(response.status_code, 404)
