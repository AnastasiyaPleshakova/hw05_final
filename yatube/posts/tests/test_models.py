from django.test import TestCase

from ..models import Comment, Group, Post, User


class PostsModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            post=cls.post,
            text='Тестовый комментарий'
        )

    def test_models_have_correct_object_names(self):
        """Корректная работа __str__ у моделей."""
        post = self.post
        group = self.group
        comment = self.comment
        expected_object_name = [
            (post, post.text[:15]),
            (group, group.title),
            (comment, comment.text[:15])
        ]
        for model, expected_value in expected_object_name:
            with self.subTest(model=model):
                self.assertEqual(str(model), expected_value)

    def test_verbose_name(self):
        """Использование корректных verbose_name."""
        post = self.post
        field_verboses = [
            ('text', 'Текст поста'),
            ('author', 'Автор'),
            ('group', 'Группа'),
            ('pub_date', 'Дата публикации'),
        ]
        for field, expected_value in field_verboses:
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name,
                    expected_value
                )

    def test_help_texts(self):
        """Использование корректных help_texts."""
        post = self.post
        help_texts = [
            ('text', 'Текст нового поста'),
            ('group', 'Группа, к которой будет относиться пост'),
        ]
        for field, expected_value in help_texts:
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text,
                    expected_value
                )
