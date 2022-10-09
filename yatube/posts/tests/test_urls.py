from http import HTTPStatus

from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post, User


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='author')
        cls.user_non_author = User.objects.create_user(username='non_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.urls = (
            ('posts:home_page', None),
            ('posts:group_posts', (cls.group.slug,)),
            ('posts:profile', (cls.user_author.username,)),
            ('posts:post_detail', (cls.post.pk,)),
            ('posts:post_create', None,),
            ('posts:post_edit', (cls.post.pk,)),
            ('posts:add_comment', (cls.post.pk,)),
            ('posts:follow_index', None),
            ('posts:profile_follow', (cls.user_author.username,)),
            ('posts:profile_unfollow', (cls.user_author.username,)),
        )

    def setUp(self) -> None:
        self.authorized_client_author = Client()
        self.authorized_non_author = Client()
        self.authorized_client_author.force_login(self.user_author)
        self.authorized_non_author.force_login(self.user_non_author)

    def test_reverse(self):
        """Проверяем корректность ссылок."""
        urls = (
            ('posts:home_page', None, '/'),
            (
                'posts:group_posts',
                (self.group.slug,),
                f'/group/{self.group.slug}/'
            ),
            (
                'posts:profile',
                (self.user_author.username,),
                f'/profile/{self.user_author.username}/'
            ),
            ('posts:post_detail', (self.post.pk,), f'/posts/{self.post.pk}/'),
            ('posts:post_create', None, '/create/'),
            (
                'posts:post_edit',
                (self.post.pk,),
                f'/posts/{self.post.pk}/edit/'
            ),
            (
                'posts:add_comment',
                (self.post.pk,),
                f'/posts/{self.post.pk}/comment/'
            ),
            ('posts:follow_index', None, '/follow/'),
            (
                'posts:profile_follow',
                (self.user_author.username,),
                f'/profile/{self.user_author.username}/follow/',
            ),
            (
                'posts:profile_unfollow',
                (self.user_author.username,),
                f'/profile/{self.user_author.username}/unfollow/',
            ),
        )
        for name, argument, url in urls:
            with self.subTest(name=name):
                self.assertEqual(reverse(name, args=argument), url)

    def test_url_for_any_user(self):
        """Доступность страниц для любого пользователя."""
        for name, argument in self.urls:
            with self.subTest(name=name):
                if name in (
                        'posts:post_create', 'posts:post_edit',
                        'posts:add_comment', 'posts:follow_index',
                        'posts:profile_follow', 'posts:profile_unfollow',
                ):
                    reverse_login = reverse('users:login')
                    reverse_name = reverse(name, args=argument)
                    self.assertRedirects(
                        self.client.get(reverse_name),
                        f'{reverse_login}?next={reverse_name}'
                    )
                else:
                    self.assertEqual(
                        self.client.get(
                            reverse(name, args=argument)).status_code,
                        HTTPStatus.OK
                    )

    def test_url_create_for_authorized_not_author_user(self):
        """Доступность страниц для авторизованного
        пользователя не являющегося автором.
        """
        for name, argument in self.urls:
            with self.subTest(name=name):
                if name in (
                        'posts:post_edit', 'posts:add_comment',
                        'posts:profile_follow', 'posts:profile_unfollow',
                ):
                    if name in (
                            'posts:profile_follow',
                            'posts:profile_unfollow',
                    ):
                        self.assertRedirects(
                            self.authorized_non_author.get(
                                reverse(name, args=argument)),
                            f'/profile/{self.user_author.username}/'
                        )
                    else:
                        self.assertRedirects(
                            self.authorized_non_author.get(
                                reverse(name, args=argument)),
                            f'/posts/{self.post.pk}/'
                        )
                else:
                    self.assertEqual(
                        self.authorized_non_author.get(
                            reverse(name, args=argument)).status_code,
                        HTTPStatus.OK
                    )

    def test_url_create_for_authorized_author_user(self):
        """Доступность страниц для авторизованного
         пользователя являющегося автором.
        """
        for name, argument in self.urls:
            with self.subTest(name=name):
                if name in (
                        'posts:add_comment',
                        'posts:profile_follow',
                        'posts:profile_unfollow',
                ):
                    if name in 'posts:add_comment':
                        self.assertRedirects(
                            self.authorized_non_author.get(
                                reverse(name, args=argument)),
                            f'/posts/{self.post.pk}/'
                        )
                    else:
                        self.assertRedirects(
                            self.authorized_non_author.get(
                                reverse(name, args=argument)),
                            f'/profile/{self.user_author.username}/'
                        )
                else:
                    self.assertEqual(
                        self.authorized_client_author.get(
                            reverse(name, args=argument)).status_code,
                        HTTPStatus.OK
                    )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        urls_name = (
            ('posts:home_page', None, 'posts/index.html'),
            ('posts:group_posts', (self.group.slug,), 'posts/group_list.html'),
            (
                'posts:profile',
                (self.user_author.username,),
                'posts/profile.html'
            ),
            ('posts:post_detail', (self.post.pk,), 'posts/post_detail.html'),
            ('posts:post_create', None, 'posts/post_create.html'),
            ('posts:post_edit', (self.post.pk,), 'posts/post_create.html'),
            ('posts:follow_index', None, 'posts/follow.html'),
        )
        for name, argument, template in urls_name:
            with self.subTest(template=template):
                response = self.authorized_client_author.get(
                    reverse(name, args=argument)
                )
                self.assertTemplateUsed(response, template)

    def test_not_found_page(self):
        """Страница с неизвестным адресом не найдена
        и использует кастомный шаблон.
        """
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
