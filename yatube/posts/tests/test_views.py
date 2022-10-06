import shutil
import tempfile


from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPageTests(TestCase):
    ZERO = 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
            post=cls.post,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def helper_function_check_context(self, response, flag=False):
        if flag:
            post = response.context['post']
        else:
            post = response.context['page_obj'][self.ZERO]
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Правильный контекст для шаблона index.html."""
        response = self.authorized_client.get(reverse('posts:home_page'))
        self.helper_function_check_context(response)

    def test_post_detail_page_show_correct_context(self):
        """Правильный контекст для шаблона post_detail.html."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        self.helper_function_check_context(response, True)
        self.assertEqual(response.context['comments'][self.ZERO], self.comment)

    def test_group_list_page_show_correct_context(self):
        """Правильный контекст для шаблона group_list.html."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=(self.group.slug,))
        )
        self.helper_function_check_context(response)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_page_show_correct_context(self):
        """Правильный контекст для шаблона profile.htmll."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user.username,))
        )
        self.helper_function_check_context(response)
        self.assertEqual(response.context['author'], self.user)

    def test_create_page_show_correct_context(self):
        """Формирование шаблонов create и edit с правильным контекстом."""
        urls_name = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.pk,)),
        )
        form_fields = [
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
        ]
        for name, argument in urls_name:
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, args=argument))
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context.get('form'), PostForm)
                for value, expected in form_fields:
                    with self.subTest(value=value):
                        self.assertIsInstance(
                            response.context.get('form').fields.get(value),
                            expected
                        )

    def test_post_not_included_another_group(self):
        """Пост не попал в другую группу."""
        group = Group.objects.create(
            title='Новая группа',
            slug='new_slug',
            description='Описание группы',
        )
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=(group.slug,)))
        self.assertEqual(len(response.context['page_obj']), self.ZERO)
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=(self.group.slug,)))
        post = response.context['page_obj'][self.ZERO]
        self.assertTrue(post.group)

    def test_cache_index(self):
        """Список постов хранится в кэше заданное время"""
        first_response = self.authorized_client.get(reverse('posts:home_page'))
        post = Post.objects.first()
        post.text = 'Новый пост'
        post.save()
        self.assertEqual(
            first_response.content,
            self.authorized_client.get(reverse('posts:home_page')).content
        )
        cache.clear()
        self.assertNotEqual(
            first_response.content,
            self.authorized_client.get(reverse('posts:home_page')).content
        )


class FollowTests(TestCase):
    COUNT = 1

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.following = User.objects.create_user(username='following')
        cls.post = Post.objects.create(
            author=cls.following,
            text='Тестовый пост',
        )

    def setUp(self) -> None:
        self.authorized_follower = Client()
        self.authorized_following = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_following.force_login(self.following)

    def test_follow_for_authorized_user(self):
        """Авторизированный пользователь может подписываться
        на пользователей и отписываться от них."""
        count_following = Follow.objects.count()
        reverses = (
            ('posts:profile_follow', (self.following.username,), self.COUNT),
            (
                'posts:profile_unfollow',
                (self.following.username,),
                count_following
            ),
        )
        for name, argument, count in reverses:
            with self.subTest(name=name):
                self.authorized_follower.get(reverse(name, args=argument))
                self.assertEqual(Follow.objects.count(), count)
                self.assertRedirects(
                    self.authorized_follower.get(reverse(name, args=argument)),
                    reverse('posts:follow_index')
                )

    def test_follow_page_show_correct_context(self):
        """Правильный контекст для шаблона follow.htmll."""
        self.authorized_follower.get(
            reverse('posts:profile_follow',
                    args=(self.following.username,))
        )
        response = self.authorized_follower.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), self.COUNT)
        post = response.context['page_obj'][self.COUNT - self.COUNT]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        response = self.authorized_following.get(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context['page_obj']),
            self.COUNT - self.COUNT
        )
