from http import HTTPStatus
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsCreateFormTests(TestCase):
    COUNT_OBJECTS = 1
    COUNT_POSTS_OF_PAGE = 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def helper_function_check_create_post(self, response, form_data):
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(self.user.username,))
        )
        self.assertEqual(Post.objects.count(), self.COUNT_OBJECTS)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'], ' Некорректный текст')
        self.assertEqual(
            post.group.pk,
            form_data['group'],
            'Некорректная группа'
        )
        self.assertEqual(post.author, self.user, 'Некорректный автор')

    def test_posts_create_auth_user_without_img(self):
        """Валидная форма создаёт запись без картинки
        в Posts для авторизованного пользователя.
        """
        Post.objects.all().delete()
        form_data = {
            'text': 'Тестовая публикация',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.helper_function_check_create_post(response, form_data)

    def test_posts_create_auth_user_with_img(self):
        """Валидная форма создаёт запись с картинкой
        в Posts для авторизованного пользователя.
        """
        Post.objects.all().delete()
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
        form_data = {
            'text': 'Тестовая публикация',
            'group': self.group.pk,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.helper_function_check_create_post(response, form_data)

    def test_posts_create_guest(self):
        """Валидная форма не создаёт запись в Posts
        для неавторизованного пользователя.
        """
        form_data = {
            'text': 'Новый текст',
            'group': '',
        }
        count_post_up = Post.objects.count()
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        count_post_after = Post.objects.count()
        self.assertEqual(
            count_post_up,
            count_post_after,
            'Изменилось количество постов'
        )

    def test_posts_edit(self):
        """Валидная форма изменяет запись в Posts."""
        group = Group.objects.create(
            title='Новая группа',
            slug='new-slug',
            description='Новое описание',)
        form_data = {
            'text': 'Новый текст',
            'group': group.pk
        }
        count_post_up = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        count_post_after = Post.objects.count()
        self.assertEqual(
            count_post_up,
            count_post_after,
            'Изменилось количество постов'
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'], 'Некорректный текст')
        self.assertEqual(post.group.pk, form_data['group'])
        self.assertEqual(post.author, self.user, 'Некорректный автор')
        response_group = self.authorized_client.get(
            reverse('posts:group_posts', args=(self.post.group.slug,))
        )
        self.assertEqual(response_group.status_code, HTTPStatus.OK)
        self.assertEqual(
            len(response_group.context['page_obj']),
            self.COUNT_POSTS_OF_PAGE
        )

    def test_label(self):
        """Использование корректных labels."""
        field_labels = (
            (self.form.fields['text'].label, 'Текст поста'),
            (self.form.fields['group'].label, 'Группа'),
        )
        for field_label, expected_values in field_labels:
            with self.subTest(field_label=field_label):
                self.assertEqual(field_label, expected_values)

    def test_help_text(self):
        """Использование корректных help_texts."""
        help_test_text = 'Текст нового поста'
        help_test_group = 'Группа, к которой будет относиться пост'
        field_help_texts = (
            (self.form.fields['text'].help_text, help_test_text),
            (self.form.fields['group'].help_text, help_test_group),
        )
        for field_help_text, expected_values in field_help_texts:
            with self.subTest(field_help_text=field_help_text):
                self.assertEqual(field_help_text, expected_values)

    def test_not_add_comment_guest(self):
        """Валидная форма не создаёт комментарий
        для неавторизованного пользователя."""
        post = Post.objects.first()
        count_comment_up = post.comments.count()
        self.client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data={'text': 'Новый комментарий', },
            follow=True
        )
        self.assertEqual(post.comments.count(), count_comment_up)

    def test_add_comment_auth_user(self):
        """Валидная форма создаёт комментарий
        для авторизованного пользователя."""
        post = Post.objects.first()
        form_data = {'text': 'Новый комментарий', }
        count_comment_up = post.comments.count()
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            post.comments.count(),
            count_comment_up + self.COUNT_OBJECTS
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        self.assertEqual(post.comments.first().text, form_data['text'])
