from django.conf import settings as s
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PaginatorViewsTest(TestCase):
    COUNT_TEST_POSTS = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.follower = User.objects.create_user(username='follower')
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

    def setUp(self) -> None:
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)
        # остановилась на варианте единого теста,
        # а это был первый вариант с использованием
        # раздельных тестов (не могу пока понять,
        # где лучше разделить, а где объединить тесты)
        # self.urls_name = {
        #     'posts:home_page': None,
        #     'posts:group_posts': (self.group.slug,),
        #     'posts:profile': (self.user.username,),
        # }
        # self.page_data = (
        #     ('?page=1', s.COUNT_OBJECTS),
        #     ('?page=2', self.COUNT_TEST_POSTS - s.COUNT_OBJECTS)
        # )

    # def test_count_of_posts_per_page_guest(self):
    #     """Проверка количества постов на страницах
    #     для любого пользователя."""
    #     for name, argument in self.urls_name.items():
    #         with self.subTest(name=name):
    #             for number_page, count_posts in self.page_data:
    #                 with self.subTest():
    #                     response = self.client.get(
    #                         reverse(name, args=argument) + number_page
    #                     )
    #                     self.assertEqual(
    #                         len(response.context['page_obj']),
    #                         count_posts,
    #                         f'Некорректное количество постов'
    #                         f'на странице: {number_page}'
    #                     )
    #
    # def test_count_of_posts_per_page_follower(self):
    #     """Проверка количества постов на страницах
    #     для авторизиованного пользователя."""
    #     self.urls_name['posts:follow_index'] = None
    #     self.authorized_client.get(
    #         reverse('posts:profile_follow',
    #                 args=(self.user.username,))
    #     )
    #     for name, argument in self.urls_name.items():
    #         with self.subTest(name=name):
    #             for number_page, count_posts in self.page_data:
    #                 with self.subTest():
    #                     response = self.authorized_client.get(
    #                         reverse(name, args=argument) + number_page
    #                         )
    #                     self.assertEqual(
    #                          len(response.context['page_obj']),
    #                          count_posts,
    #                          f'Некорректное количество постов'
    #                          f'на странице: {number_page}'
    #                         )

    def test_count_of_posts_per_page(self):
        """Проверка количества постов на страницах
        для любого пользователя."""
        urls_name = (
            ('posts:home_page', None, self.client,),
            ('posts:group_posts', (self.group.slug,), self.client,),
            ('posts:profile', (self.user.username,), self.client,),
            ('posts:follow_index', None, self.authorized_client,),
        )
        page_data = (
            ('?page=1', s.COUNT_OBJECTS),
            ('?page=2', self.COUNT_TEST_POSTS - s.COUNT_OBJECTS)
        )
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    args=(self.user.username,))
        )
        for name, argument, type_client in urls_name:
            with self.subTest(name=name):
                for number_page, count_posts in page_data:
                    with self.subTest():
                        response = type_client.get(
                            reverse(name, args=argument) + number_page
                        )
                        self.assertEqual(
                            len(response.context['page_obj']),
                            count_posts,
                            f'Некорректное количество постов'
                            f'на странице: {number_page}'
                        )
