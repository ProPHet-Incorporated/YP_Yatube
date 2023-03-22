import shutil
import tempfile
from collections import namedtuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

from .utils import colorize_msg

User = get_user_model()
Pagetuple = namedtuple(
    'Pagetuple', ['namespace', 'kwargs', 'template', 'verbose_name']
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='test-user')

        cls.test_group = Group.objects.create(
            title='test_group',
            slug='test_group_slug'
        )
        cls.tmp_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.page_post_create = Pagetuple(
            'posts:post_create',
            None,
            'posts/create_post.html',
            'форма создания поста'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_new_post_without_group_created_via_form(self):
        msg_form_name = 'Форма по добавлению поста (без группы)'
        posts_count = Post.objects.count()
        form_data = {'text': 'test-text'}
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        msg = colorize_msg(
            f'{msg_form_name} не перенаправляет на success-страницу'
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}
        ), msg_prefix=msg)
        msg = colorize_msg(f'{msg_form_name} не создаёт пост')
        self.assertEqual(Post.objects.count(), posts_count + 1, msg)

    def test_new_post_with_group_created_via_form(self):
        msg_form_name = 'Форма по добавлению поста (с группой)'
        posts_count = Post.objects.count()
        form_data = {
            'text': 'test-text',
            'group': self.test_group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        msg = colorize_msg(
            f'{msg_form_name} не перенаправляет на success-страницу'
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}
        ), msg_prefix=msg)
        msg = colorize_msg(f'{msg_form_name} не создаёт пост')
        self.assertEqual(Post.objects.count(), posts_count + 1, msg)

    def test_post_edited_via_form(self):
        tmp_post = Post.objects.create(
            text='test-text-created-manually',
            author=self.user
        )

        form_data = {'text': 'test-text-edited', }
        self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': tmp_post.id}),
            data=form_data,
            follow=True
        )
        self.assertTrue(Post.objects.filter(text=form_data['text']).exists())

    def test_post_with_image_creates_via_form(self):
        msg_form_name = 'Форма по добавлению поста (с группой)'

        posts_count = Post.objects.count()
        client = self.authorized_client
        page = self.page_post_create
        form_data = {
            'text': 'test-text-edited',
            'image': self.tmp_image
        }
        client.post(reverse(page.namespace), data=form_data, follow=True)
        msg = colorize_msg(f'{msg_form_name} не создаёт пост')
        self.assertEqual(Post.objects.count(), posts_count + 1, msg)


class PostsFormTestComments(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp_user = User.objects.create(username='test-user')
        cls.tmp_post = Post.objects.create(
            text='post-text',
            author=cls.tmp_user,
        )
        cls.page_add_comment = Pagetuple(
            'posts:add_comment',
            {'post_id': cls.tmp_post.id},
            'posts/post_detail.html',
            'страница создания коммента под постом'
        )

    def setUp(self):
        self.guest_client = Client()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.tmp_user)

    def try_to_create_a_comment(self, client):
        page = self.page_add_comment
        form_data = {'text': 'comment-text', }
        client.post(
            reverse(page.namespace, kwargs=page.kwargs),
            data=form_data,
            follow=True
        )

    def test_authorized_user_can_comment(self):
        client = self.authorized_client
        count_old = Comment.objects.count()
        self.try_to_create_a_comment(client)
        count_new = Comment.objects.count()
        msg = colorize_msg(
            'Авторизованный пользователь не смог создать коммент'
        )
        self.assertEqual(count_new, count_old + 1, msg)

    def test_unauthorized_user_cant_comment(self):
        client = self.guest_client
        count_old = Comment.objects.count()
        self.try_to_create_a_comment(client)
        count_new = Comment.objects.count()
        msg = colorize_msg(
            'Неавторизованный пользователь смог создать коммент'
        )
        self.assertEqual(count_new, count_old, msg)
