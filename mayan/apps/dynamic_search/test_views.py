from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase

from documents.models import DocumentType
from documents.search import document_search
from documents.test_models import (
    TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME, TEST_ADMIN_EMAIL,
    TEST_DOCUMENT_TYPE, TEST_SMALL_DOCUMENT_PATH
)


class Issue46TestCase(TestCase):
    """
    Functional tests to make sure issue 46 is fixed
    """

    def setUp(self):
        self.admin_user = User.objects.create_superuser(username=TEST_ADMIN_USERNAME, email=TEST_ADMIN_EMAIL, password=TEST_ADMIN_PASSWORD)
        self.client = Client()
        # Login the admin user
        logged_in = self.client.login(username=TEST_ADMIN_USERNAME, password=TEST_ADMIN_PASSWORD)
        self.assertTrue(logged_in)
        self.assertTrue(self.admin_user.is_authenticated())

        self.document_count = 30

        self.document_type = DocumentType.objects.create(label=TEST_DOCUMENT_TYPE)

        # Upload 30 instances of the same test document
        for i in range(self.document_count):
            with open(TEST_SMALL_DOCUMENT_PATH) as file_object:
                self.document_type.new_document(
                    file_object=File(file_object),
                    label='test document',
                )

    def test_advanced_search_past_first_page(self):
        # Make sure all documents are returned by the search
        model_list, result_set, elapsed_time = document_search.search({'label': 'test document'}, user=self.admin_user)
        self.assertEqual(len(result_set), self.document_count)

        # Funcitonal test for the first page of advanced results
        response = self.client.get(reverse('search:results'), {'label': 'test'})
        self.assertContains(response, 'Total (1 - 20 out of 30) (Page 1 of 2)', status_code=200)

        # Functional test for the second page of advanced results
        response = self.client.get(reverse('search:results'), {'label': 'test', 'page': 2})
        self.assertContains(response, 'Total (21 - 30 out of 30) (Page 2 of 2)', status_code=200)
