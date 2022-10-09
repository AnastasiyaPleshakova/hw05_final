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
        cls.uploaded = SimpleUploadedFile(
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
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
            post=cls.post,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

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
            ('image', forms.fields.ImageField),
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
        Post.objects.all().delete()
        form_data = {
            'text': 'Новый пост',
            'group': self.group.pk,
            'image': self.uploaded
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        first_request = self.authorized_client.get(reverse('posts:home_page'))
        Post.objects.all().delete()
        second_request = self.authorized_client.get(reverse('posts:home_page'))
        self.assertEqual(first_request.content, second_request.content)
        cache.clear()
        third_request = self.authorized_client.get(reverse('posts:home_page'))
        self.assertNotEqual(first_request.content, third_request.content)


class FollowTests(TestCase):
    COUNT = 1
    FIRST_OBJECTS = 0

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
        """Авторизированный пользователь может
        подписываться на пользователей."""
        self.authorized_follower.get(reverse(
            'posts:profile_follow',
            args=(self.following.username,))
        )
        follow = Follow.objects.first()
        self.assertEqual(follow.user, self.follower)
        self.assertEqual(follow.author, self.following)
        self.assertEqual(Follow.objects.count(), self.COUNT)

    def test_unfollow_for_authorized_user(self):
        """Авторизированный пользователь может
        отписываться от пользователей."""
        Follow.objects.create(
            user=self.follower,
            author=self.following,
        )
        count_after_follow = Follow.objects.count()
        self.authorized_follower.get(reverse(
            'posts:profile_unfollow',
            args=(self.following.username,))
        )
        self.assertNotEqual(count_after_follow, Follow.objects.count())

    def test_follow_page_show_correct_context(self):
        """Правильный контекст для шаблона follow.htmll."""
        Follow.objects.create(
            user=self.follower,
            author=self.following,
        )
        response = self.authorized_follower.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), self.COUNT)
        post = response.context['page_obj'][self.FIRST_OBJECTS]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        response = self.authorized_following.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), self.FIRST_OBJECTS)

    def test_follow_on_oneself(self):
        count_follow = Follow.objects.count()
        self.authorized_follower.get(reverse(
            'posts:profile_follow',
            args=(self.follower.username,))
        )
        self.assertEqual(count_follow, Follow.objects.count())

    def test_refollow(self):
        Follow.objects.create(
            user=self.follower,
            author=self.following,
        )
        count_follow = Follow.objects.count()
        self.authorized_follower.get(reverse(
            'posts:profile_follow',
            args=(self.following.username,))
        )
        self.assertEqual(count_follow, Follow.objects.count())
