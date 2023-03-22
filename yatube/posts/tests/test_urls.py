from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from posts.models import Group, Post

from .utils import colorize_msg

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='user-author')
        cls.user = User.objects.create_user(username='NoName')
        cls.tmp_post = Post.objects.create(
            text='test text',
            author=cls.author,
        )
        cls.tmp_group = Group.objects.create(
            title='test_group',
            slug='test_group_slug'
        )

        cls.url_first_post = f'/posts/{cls.tmp_post.id}/'
        cls.url_first_post_edit = cls.url_first_post + 'edit/'

        cls.urls_common = {
            '/': 'posts/index.html',
            f'/group/{cls.tmp_group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user.username}/': 'posts/profile.html',
            cls.url_first_post: 'posts/post_detail.html',
        }
        cls.urls_private = {
            cls.url_first_post_edit: 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        cls.urls_all = {}
        cls.urls_all.update(cls.urls_common)
        cls.urls_all.update(cls.urls_private)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

        self.author_client = Client()
        self.author_client.force_login(self.author)

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_all_pages_accessed_by_author(self):
        """Тест - все страницы доступны автору."""
        for page in PostsURLTests.urls_all:
            with self.subTest(address=page):
                response = self.author_client.get(page)
                msg = colorize_msg(
                    f'Страница "{page}" недоступна для автора'
                )
                self.assertEqual(response.status_code, HTTPStatus.OK, msg)

    def test_common_pages_accessed_by_guest(self):
        """Тест - общие страницы доступны гостю."""
        for page in PostsURLTests.urls_common:
            with self.subTest(address=page):
                response = self.guest_client.get(page)
                msg = colorize_msg(
                    f'Страница "{page}" недоступна для гостя'
                )
                self.assertEqual(response.status_code, HTTPStatus.OK, msg)

    def test_private_pages_redirect_guest(self):
        """Тест - приватные страницы перенаправляют гостя на логин."""
        for page in PostsURLTests.urls_private:
            with self.subTest(address=page):
                response = self.guest_client.get(page)
                msg = colorize_msg(
                    f'Страница "{page}" не перенаправляет гостя '
                    'на страницу логина'
                )
                self.assertRedirects(
                    response, ('/auth/login/?next=' + page), msg_prefix=msg
                )

    def test_edit_foreign_post_redirects_authorized_client(self):
        """При редактировании чужого поста пользователь
        отправляется на страницу поста.
        """
        page = self.url_first_post_edit
        response = self.authorized_client.get(page)
        msg = colorize_msg(
            f'Страница "{page}" не перенаправляет пользователя'
            'на страницу этого поста без возможности редактирования'
        )
        self.assertRedirects(response, (self.url_first_post), msg_prefix=msg)

    def test_urls_uses_correct_template(self):
        """Тест на корректность используемых шаблонов."""
        for address, template in PostsURLTests.urls_all.items():
            msg = colorize_msg(
                f'Для страницы "{address}" '
                f'НЕ ИСПОЛЬЗУЕТСЯ шаблон {template}'
            )
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template, msg)
