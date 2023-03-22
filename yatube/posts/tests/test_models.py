from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post
from .utils import colorize_msg

User = get_user_model()


class PostModelTest(TestCase):
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
            text='Тестовый пост с очень длинным текстом',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        txt = self.post.text[:15]
        str_post = str(post)
        msg = colorize_msg(
            f'Пост некорректно сокращается. '
            f'Получается: "{str_post}", а должно быть "{txt}"'
        )
        self.assertEqual(str_post, txt, msg)

    def test_groups_have_correct_object_names(self):
        """Проверяем, что у групп корректно работает __str__."""
        group = PostModelTest.group
        str_group = str(group)
        txt = f'Группа: {self.group.title}'
        msg = colorize_msg(
            f'__str__ группы отображается некорректно. '
            f'{str_group}", а должно быть "{txt}"'
        )
        self.assertEqual(str(group), txt, msg)

    def test_models_have_verbose_names(self):
        """Проверяем, что у моделей и групп есть verbose_name."""
        post = PostModelTest.post
        group = PostModelTest.group
        testing_data = {
            post._meta.get_field('text').verbose_name: 'Текст поста',
            group._meta.verbose_name: 'Сообщество',
        }
        for verbose_name, expected in testing_data.items():
            msg = colorize_msg(
                f'verbose_name указано некорректно. "{verbose_name}",'
                f' а должно быть "{expected}"'
            )
            with self.subTest(template=verbose_name):
                self.assertEqual(verbose_name, expected, msg)

    def test_models_have_help_text(self):
        post = PostModelTest.post
        text_help_text = post._meta.get_field('text').help_text
        gr_help_text = post._meta.get_field('group').help_text

        testing_data = {
            text_help_text: 'Напишите здесь основной текст',
            gr_help_text: 'Выберите группу, в которой опубликовать этот пост',
        }
        for help_text, expected in testing_data.items():
            msg = colorize_msg(
                f'help_text указан некорректно. "{help_text}",'
                f' а должно быть "{expected}"'
            )
            with self.subTest(template=help_text):
                self.assertEqual(help_text, expected, msg)
