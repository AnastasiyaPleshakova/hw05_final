from http import HTTPStatus

from django.test import TestCase, Client


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_static_page(self):
        static_url = (
            '/about/author/',
            '/about/tech/',
        )
        for url in static_url:
            with self.subTest(url=url):
                self.assertEqual(
                    self.guest_client.get(url).status_code, HTTPStatus.OK)
