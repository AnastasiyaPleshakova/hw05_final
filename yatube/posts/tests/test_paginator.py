from django.conf import settings as s
from django.test import TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PaginatorViewsTest(TestCase):
    COUNT_TEST_POSTS = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts = []
        cls.posts = (Post(
            author=cls.user,
            text=f'Тестовый пост {post_number}',
            group=cls.group) for post_number in range(cls.COUNT_TEST_POSTS))
        Post.objects.bulk_create(cls.posts)

    def test_count_of_posts_per_page(self):
        """Проверка количества постов на страницах."""
        urls_name = (
            ('posts:home_page', None),
            ('posts:group_posts', (self.group.slug,)),
            ('posts:profile', (self.user.username,)),
        )
        page_data = [
            ('?page=1', s.COUNT_OBJECTS),
            ('?page=2', self.COUNT_TEST_POSTS - s.COUNT_OBJECTS)
        ]
        for name, argument in urls_name:
            with self.subTest(name=name):
                for number_page, count_posts in page_data:
                    with self.subTest():
                        response = self.client.get(
                            reverse(name, args=argument) + number_page
                        )
                        self.assertEqual(
                            len(response.context['page_obj']),
                            count_posts,
                            f'Некорректное количество постов'
                            f'на странице: {number_page}'
                        )
