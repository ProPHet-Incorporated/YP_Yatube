import shutil
import tempfile
from collections import namedtuple

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.forms import PostForm
from posts.models import Comment, Follow, Group, Post

from .utils import colorize_msg

User = get_user_model()
Pagetuple = namedtuple(
    'Pagetuple', ['namespace', 'kwargs', 'template', 'verbose_name']
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='test-user-PostsViewsTest')

        cls.tmp_image_bytes = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.tmp_image = SimpleUploadedFile(
            name='small.gif',
            content=cls.tmp_image_bytes,
            content_type='image/gif'
        )
        cls.test_group = Group.objects.create(
            title='group-name',
            slug='group-slug',
        )
        cls.tmp_post = Post.objects.create(
            text='post-text',
            author=cls.user,
            group=cls.test_group,
            image=cls.tmp_image,
        )

        cls.page_index = Pagetuple(
            'posts:index',
            None,
            'posts/index.html',
            'индекс'
        )
        cls.page_group_list = Pagetuple(
            'posts:group_list',
            {'slug': cls.test_group.slug},
            'posts/group_list.html',
            'список постов группы'
        )
        cls.page_profile = Pagetuple(
            'posts:profile',
            {'username': cls.user.username},
            'posts/profile.html',
            'список постов пользователя'
        )
        cls.page_post_detail = Pagetuple(
            'posts:post_detail',
            {'post_id': cls.tmp_post.id},
            'posts/post_detail.html',
            'индивидуальная страница поста'
        )
        cls.page_post_create = Pagetuple(
            'posts:post_create',
            None,
            'posts/create_post.html',
            'форма создания поста'
        )
        cls.page_post_edit = Pagetuple(
            'posts:post_edit',
            {'post_id': cls.tmp_post.id},
            'posts/create_post.html',
            'форма редактирования поста'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_templates_from_namespaces(self):
        """Тест - namespace вызывает корректный шаблон."""
        authorized_client = self.authorized_client
        pages = [
            self.page_index,
            self.page_group_list,
            self.page_profile,
            self.page_post_detail,
            self.page_post_create,
            self.page_post_edit,
        ]

        for page in pages:
            with self.subTest(template=page.template):
                reverse_name = reverse(page.namespace, kwargs=page.kwargs)
                response = authorized_client.get(reverse_name)
                msg = colorize_msg(
                    f'Для страницы "{reverse_name}" '
                    f'НЕ ИСПОЛЬЗУЕТСЯ шаблон {page.template}'
                )
                self.assertTemplateUsed(response, page.template, msg)

    def create_msg(self, page, test_obj, expected):
        msg = (
            f'На странице "{page.verbose_name}" "{test_obj}" не совпадает '
            f'с фикстурой "{expected}"'
        )
        return colorize_msg(msg)

    def context_test_helper(self, page, paginator):
        client = self.authorized_client
        response = client.get(reverse(page.namespace, kwargs=page.kwargs))
        context = response.context.get('post')
        if paginator is True:
            page_obj = response.context.get('page_obj')
            msg = colorize_msg(
                f'На странице {page.namespace} не найден объект "page_obj"'
            )
            self.assertIsInstance(page_obj, Page, msg)
            context = page_obj[0]

        msg = colorize_msg(
            f'На странице {page.verbose_name} объект поста не найден'
        )
        self.assertIsInstance(context, Post, msg)
        test_this = {
            context.text: self.tmp_post.text,
            context.author: self.tmp_post.author,
            context.group: self.tmp_post.group,
            context.image: self.tmp_post.image
        }
        for test_obj, expected in test_this.items():
            with self.subTest(address=test_obj):
                msg = self.create_msg(page, test_obj, expected)
                self.assertEqual(test_obj, expected, msg)
        return response.context

    def test_context_index(self):
        page = self.page_index
        paginator = True
        self.context_test_helper(page, paginator)

    def test_context_post_detail(self):
        page = self.page_post_detail
        paginator = False
        self.context_test_helper(page, paginator)

    def test_context_group_list(self):
        page = self.page_group_list
        paginator = True
        context = self.context_test_helper(page, paginator)
        self.assertEqual(context.get('group'), self.test_group)

    def test_context_profile(self):
        page = self.page_profile
        paginator = True
        context = self.context_test_helper(page, paginator)
        self.assertEqual(context.get('author'), self.user)

    def test_form_create_and_edit_post(self):
        pages = [
            self.page_post_create,
            self.page_post_edit,
        ]
        for page in pages:
            with self.subTest(address=page):
                authorized_client = self.authorized_client
                response = authorized_client.get(reverse(
                    page.namespace,
                    kwargs=page.kwargs
                ))
                form_fields = {
                    'text': forms.fields.CharField,
                    'group': forms.fields.ChoiceField,
                }
                for value, expected in form_fields.items():
                    form = response.context.get('form')
                    msg = colorize_msg(
                        f'На странице "{page.verbose_name}" не найдена форма'
                    )
                    self.assertIsInstance(form, PostForm, msg)
                    form_field = form.fields.get(value)
                    msg = colorize_msg(
                        f'На странице "{page.verbose_name}" '
                        f'поле "{form_field}" '
                        f'не соответствует ожидаемому {expected}'
                    )
                    self.assertIsInstance(form_field, expected, msg)


class PostsViewsTestPaginators(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ADDITIONAL_POSTS = 3
        cls.user = User.objects.create(username='test-user-Paginators')

        cls.test_group_1 = Group.objects.create(
            title='group-name-1',
            slug='group-slug-1',
        )
        cls.test_group_2 = Group.objects.create(
            title='group-name-2',
            slug='group-slug-2',
        )
        for i in range(
            settings.NUMBER_OF_POSTS_ON_ONE_PAGE + cls.ADDITIONAL_POSTS
        ):
            Post.objects.create(
                text='post-text-group-1',
                author=cls.user,
                group=cls.test_group_1,
            )

        cls.page_index = Pagetuple(
            'posts:index',
            None,
            'posts/index.html',
            'индекс'
        )
        cls.page_group_list_1 = Pagetuple(
            'posts:group_list',
            {'slug': cls.test_group_1.slug},
            'posts/group_list.html',
            'список постов группы #1'
        )
        cls.page_group_list_2 = Pagetuple(
            'posts:group_list',
            {'slug': cls.test_group_2.slug},
            'posts/group_list.html',
            'список постов группы #2'
        )
        cls.page_profile = Pagetuple(
            'posts:profile',
            {'username': cls.user.username},
            'posts/profile.html',
            'список постов пользователя'
        )

        cls.pages_to_test = (
            cls.page_index,
            cls.page_group_list_1,
            cls.page_profile,
        )

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def single_sub_test(self, page, next_page):
        client = self.authorized_client
        response = client.get(reverse(
            page.namespace, kwargs=page.kwargs
        ) + next_page)
        page_obj = response.context.get('page_obj')
        msg = colorize_msg(
            f'На странице "{page.verbose_name}" не найден паджинатор'
        )
        self.assertIsInstance(page_obj, Page, msg)
        return page_obj

    def test_all_paginators(self):
        next_page_needed = [
            ['', settings.NUMBER_OF_POSTS_ON_ONE_PAGE],
            ['?page=2', self.ADDITIONAL_POSTS]
        ]

        for next_page in next_page_needed:
            expected_posts_count = next_page[1]
            for page in self.pages_to_test:
                with self.subTest(address=page):
                    page_obj = self.single_sub_test(page, next_page[0])
                    count = len(page_obj)
                    msg = colorize_msg(
                        f'На странице "{page.verbose_name}" '
                        f'кол-во постов {count}, '
                        f'а должно быть {expected_posts_count}'
                    )
                    self.assertEqual(count, expected_posts_count, msg)

    def test_post_in_group2_are_on_proper_page(self):
        new_post = Post.objects.create(
            text='post-text-group-2',
            author=self.user,
            group=self.test_group_2,
        )

        pages = [
            self.page_index,
            self.page_group_list_2,
            self.page_profile,
        ]
        for page in pages:
            msg = colorize_msg(
                f'Пост с группой "{new_post.group.title}" '
                f'НЕ НАЙДЕН на странице "{page.verbose_name}"'
            )
            with self.subTest(address=page):
                page_obj = self.single_sub_test(page, next_page='')
                self.assertIn(new_post, page_obj, msg)

        page = self.page_group_list_1
        with self.subTest(address=page):
            page_obj = self.single_sub_test(page, next_page='')
            msg = colorize_msg(
                f'Пост с группой "{new_post.group.title}" '
                f'НАЙДЕН на странице "{page.verbose_name}"'
            )
            self.assertNotIn(new_post, page_obj, msg)


class PostsViewsTestComments(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tmp_user = User.objects.create(username='test-user-Comments')
        cls.tmp_post = Post.objects.create(
            text='post-text',
            author=cls.tmp_user,
        )
        cls.tmp_wrong_post = Post.objects.create(
            text='post-text',
            author=cls.tmp_user,
        )
        cls.tmp_comment = Comment.objects.create(
            text='comment-text',
            author=cls.tmp_user,
            post=cls.tmp_post
        )
        cls.page_post_detail = Pagetuple(
            'posts:post_detail',
            {'post_id': cls.tmp_post.id},
            'posts/post_detail.html',
            'индивидуальная страница поста'
        )
        cls.page_wrong_post_detail = Pagetuple(
            'posts:post_detail',
            {'post_id': cls.tmp_wrong_post.id},
            'posts/post_detail.html',
            'индивидуальная страница поста'
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_comment_appears_on_post_page(self):
        client = self.guest_client
        page = self.page_post_detail
        response = client.get(reverse(
            page.namespace, kwargs=page.kwargs
        ))
        resp_comments = response.context.get('comments')
        if resp_comments is None:
            raise AssertionError(colorize_msg(
                'Ни один коммент не найден под тестовым постом'
            ))
        msg = colorize_msg('Объект не является комментом')
        self.assertIsInstance(resp_comments[0], Comment, msg)

    def test_comment_doesnt_appear_on_wrong_post_page(self):
        client = self.guest_client
        page = self.page_wrong_post_detail
        response = client.get(reverse(
            page.namespace, kwargs=page.kwargs
        ))
        context = response.context.get('comments')
        msg = colorize_msg('Коммент найден на странице другого поста')
        self.assertNotIn('comment-text', context, msg)


class TestViewsCahce(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tmp_user = User.objects.create(username='test-user-Cahce')

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

    def test_cache_index(self):
        tmp_post = Post.objects.create(
            text='post-text-1',
            author=self.tmp_user,
        )

        rev_page = reverse('posts:index')
        post_text = tmp_post.text
        client = self.guest_client

        response = client.get(rev_page)
        context = response.context.get('post')
        original_content = response.content
        msg = colorize_msg('Пост не найден на главной странице')
        self.assertEqual(post_text, context.text, msg)

        tmp_post.delete()
        response = client.get(rev_page)
        msg = colorize_msg(
            'Пост удалён. Кэш не очищен. '
            'Пост не найден на главной странице'
        )
        self.assertEqual(original_content, response.content, msg)

        cache.clear()
        response = client.get(rev_page)
        msg = colorize_msg(
            'Пост удалён. Кэш очищен. Пост найден на главной странице'
        )
        self.assertNotEqual(original_content, response.content, msg)


class TestViewFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp_user_1 = User.objects.create(username='tmp_user_Follow-1')
        cls.tmp_user_2 = User.objects.create(username='tmp_user_Follow-2')

        cls.tmp_author_1 = User.objects.create(username='tmp_user_author_1')
        cls.tmp_post_1 = Post.objects.create(
            text='post-text-1',
            author=cls.tmp_author_1,
        )

        cls.tmp_author_2 = User.objects.create(username='tmp_user_author_2')
        cls.tmp_post_2 = Post.objects.create(
            text='post-text-2',
            author=cls.tmp_author_2,
        )
        cls.page_profile_1 = Pagetuple(
            'posts:profile',
            {'username': cls.tmp_author_1.username},
            'posts/profile.html',
            'список постов автора 1'
        )
        cls.page_profile_2 = Pagetuple(
            'posts:profile',
            {'username': cls.tmp_author_2.username},
            'posts/profile.html',
            'список постов автора 2'
        )
        cls.profile_follow = Pagetuple(
            'posts:profile_follow',
            {'username': cls.tmp_author_1},
            'posts/follow.html',
            'список постов подписанных авторов'
        )
        cls.profile_unfollow = Pagetuple(
            'posts:profile_unfollow',
            {'username': cls.tmp_author_1},
            'posts/follow.html',
            'список постов подписанных авторов'
        )
        cls.profile_follow_user = Pagetuple(
            'posts:profile_follow',
            {'username': cls.tmp_user_1},
            'posts/follow.html',
            'список постов подписанных авторов'
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.tmp_user_1)

        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.tmp_user_1)

    def test_user_can_or_cant_follow_author(self):
        clients = (
            (self.guest_client, 'Гость смог подписаться на автора', 0),
            (
                self.authorized_client,
                'Авторизованный пользователь не смог подписаться на автора',
                1
            ),
        )
        page = self.profile_follow
        for client, msg, outcome in clients:
            with self.subTest(client=client):
                client.get(reverse(page.namespace, kwargs=page.kwargs,))
                count = Follow.objects.count()
                self.assertEqual(count, outcome, colorize_msg(msg))

    def test_user_can_unfollow(self):
        Follow.objects.create(
            user=self.tmp_user_2,
            author=self.tmp_author_1
        )
        page = self.profile_unfollow
        client = self.authorized_client_2
        client.get(reverse(page.namespace, kwargs=page.kwargs,))
        checking = Follow.objects.filter(
            user=self.tmp_user_2.id,
            author=self.tmp_author_1.id
        ).exists()
        msg = colorize_msg('Пользователь 2 не смог отписаться от автора 1')
        self.assertTrue(checking, msg)

    def test_user_cant_follow_himself(self):
        """Тест - пользователь не может подписаться сам на себя."""
        page = self.profile_follow_user
        client = self.authorized_client
        msg = 'Пользователь смог подписаться сам на себя'
        client.get(reverse(page.namespace, kwargs=page.kwargs,))
        count = Follow.objects.count()
        self.assertEqual(count, 0, colorize_msg(msg))

    def test_post_appears_in_the_correct_feed(self):
        Follow.objects.create(
            user=self.tmp_user_1,
            author=self.tmp_author_1,
        )
        client = self.authorized_client

        post = self.tmp_post_1
        with self.subTest(post.text):
            page = self.page_profile_1
            msg = colorize_msg('Пост автора 1 не появился в его фиде')
            response = client.get(reverse(page.namespace, kwargs=page.kwargs))
            context = response.context.get('page_obj')
            self.assertIn(post, context, msg)

        post = self.tmp_post_2
        with self.subTest(post.text):
            msg = colorize_msg('Пост автора 2 появился в фиде автора 1')
            response = client.get(reverse(page.namespace, kwargs=page.kwargs))
            context = response.context.get('page_obj')
            self.assertNotIn(post, context, msg)
