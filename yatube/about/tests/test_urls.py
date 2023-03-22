from http import HTTPStatus

from django.test import Client, TestCase

from posts.tests.utils import colorize_msg


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_unexisting_page_returns_status_404(self):
        address = '/unexisting_page/'
        response = self.guest_client.get(address)
        msg = colorize_msg(
            'Несуществующая страница не выдаёт ошибку 404'
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, msg)

    def test_unexisting_page_uses_correct_template(self):
        address = '/unexisting_page/'
        response = self.guest_client.get(address)
        msg = colorize_msg(
            'Несуществующая страница не использует шаблон core/404.html'
        )
        self.assertTemplateUsed(response, 'core/404.html', msg)
