"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_list_accounts(self):
        """It should return all of the accounts"""
        accounts = self._create_accounts(5)
        response = self.client.get(BASE_URL)
        accounts_list = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(accounts_list), 5)
        account_ids = [account.id for account in accounts]
        for account in accounts_list:
            self.assertTrue(account['id'] in account_ids)

    def test_read_an_account(self):
        """It should return an account"""
        accounts = self._create_accounts(5)
        account = accounts[0]
        account_id = account.id
        response = self.client.get(f"{BASE_URL}/{account_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account_json = response.get_json()
        account_found = Account.find(account_id)
        self.assertEqual(int(account_json['id']), account_found.id)
        self.assertEqual(account_json['name'], account_found.name)
        self.assertEqual(account_json['email'], account_found.email)
        self.assertEqual(account_json['address'], account_found.address)
        self.assertEqual(
            account_json['phone_number'],
            account_found.phone_number)
        self.assertEqual(
            account_json['date_joined'], str(
                account_found.date_joined))
        # Test non-existent account
        response = self.client.get(f"{BASE_URL}/100")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_an_account(self):
        """It should update an account"""
        # create an account
        account = AccountFactory()
        response = self.client.post(BASE_URL, json=account.serialize())
        # Post it
        # assert status_code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # get return json
        account_json = response.get_json()
        # change name value
        account_json["name"] = "test name"
        # update it
        response = self.client.put(
            f"{BASE_URL}/{account_json['id']}",
            json=account_json)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # assert the change
        new_account = response.get_json()
        self.assertEqual(new_account["name"], "test name")

    def test_delete_an_account(self):
        """It should delete an account"""
        # create an account
        account = AccountFactory()
        # post it
        response = self.client.post(BASE_URL, json=account.serialize())
        # assert status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        account_id = response.get_json()['id']
        # delete it using endpoint
        response = self.client.delete(f"{BASE_URL}/{account_id}")
        # assert status
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_method_not_allowed(self):
        """It should return method not allowed"""
        response = self.client.delete(BASE_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'}
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return a cors header"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get(
            'Access-Control-Allow-Origin'), '*')
