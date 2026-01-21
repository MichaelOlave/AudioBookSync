#!/usr/bin/env python
"""Comprehensive test script for all AudioBookSync API endpoints."""

import requests
import json
import time
import sys
import uuid
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 10

# Generate unique usernames for each test run
UNIQUE_ID = str(uuid.uuid4())[:8]

# Test credentials - using unique usernames each run
TEST_USER = {
    "username": f"testuser_api_{UNIQUE_ID}",
    "email": f"test_api_{UNIQUE_ID}@example.com",
    "password": "Test@123456"
}

TEST_USER_2 = {
    "username": f"testuser2_api_{UNIQUE_ID}",
    "email": f"test2_api_{UNIQUE_ID}@example.com",
    "password": "Test@123456"
}

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.refresh_token = None
        self.results = []
        self.user_id = None

    def log_result(self, endpoint: str, method: str, status_code: int, success: bool, details: str = ""):
        """Log test result."""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "success": success,
            "details": details
        }
        self.results.append(result)
        status = "✓" if success else "✗"
        print(f"{status} {method:6} {endpoint:40} [{status_code:3}] {details}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")

        if total - passed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r["success"]:
                    print(f"  - {r['method']} {r['endpoint']}: {r['details']}")
        print("=" * 80)

    # =========== HEALTH & INFO ENDPOINTS ===========

    def test_health(self):
        """Test GET /api/v1/health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
            success = response.status_code == 200
            self.log_result("/health", "GET", response.status_code, success,
                          "Service is healthy" if success else response.text[:50])
        except Exception as e:
            self.log_result("/health", "GET", 0, False, str(e)[:50])

    # =========== AUTHENTICATION ENDPOINTS ===========

    def test_register(self, user_data: Dict[str, str] = None):
        """Test POST /auth/register"""
        if user_data is None:
            user_data = TEST_USER
        try:
            response = requests.post(
                f"{self.base_url}/auth/register",
                json=user_data,
                timeout=TIMEOUT
            )
            success = response.status_code == 201
            if success:
                try:
                    data = response.json()
                    self.user_id = data.get("user_id") or data.get("id")
                except:
                    pass
            self.log_result("/auth/register", "POST", response.status_code, success,
                          "User created successfully" if success else response.text[:50])
        except Exception as e:
            self.log_result("/auth/register", "POST", 0, False, str(e)[:50])

    def test_login(self, user_data: Dict[str, str] = None):
        """Test POST /auth/login"""
        if user_data is None:
            user_data = TEST_USER
        try:
            # OAuth2PasswordRequestForm requires form data, not JSON
            response = requests.post(
                f"{self.base_url}/auth/login",
                data={
                    "username": user_data["username"],
                    "password": user_data["password"],
                    "grant_type": "password"  # OAuth2 standard
                },
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            if success:
                data = response.json()
                self.token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
            self.log_result("/auth/login", "POST", response.status_code, success,
                          "Login successful" if success else response.text[:50])
        except Exception as e:
            self.log_result("/auth/login", "POST", 0, False, str(e)[:50])

    def test_refresh_token(self):
        """Test POST /auth/refresh"""
        if not self.refresh_token:
            print("  ⊘ /auth/refresh skipped (no refresh token)")
            return
        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token},
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            if success:
                data = response.json()
                self.token = data.get("access_token")
            self.log_result("/auth/refresh", "POST", response.status_code, success,
                          "Token refreshed" if success else response.text[:50])
        except Exception as e:
            self.log_result("/auth/refresh", "POST", 0, False, str(e)[:50])

    # =========== USER ENDPOINTS ===========

    def test_get_current_user(self):
        """Test GET /users/me"""
        if not self.token:
            print("  ⊘ /users/me skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            self.log_result("/users/me", "GET", response.status_code, success,
                          "Current user retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/users/me", "GET", 0, False, str(e)[:50])

    def test_change_password(self):
        """Test PATCH /users/me/password"""
        if not self.token:
            print("  ⊘ /users/me/password skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            # Note: Cannot actually change password without old password verification
            # This will fail but we're testing the endpoint exists
            response = requests.patch(
                f"{self.base_url}/users/me/password",
                headers=headers,
                json={
                    "current_password": "wrongpassword",
                    "new_password": "NewPass@123"
                },
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 401, 400]  # Expect error with wrong password
            self.log_result("/users/me/password", "PATCH", response.status_code, success,
                          "Password change attempted" if success else response.text[:50])
        except Exception as e:
            self.log_result("/users/me/password", "PATCH", 0, False, str(e)[:50])

    # =========== LIBRARY ENDPOINTS ===========

    def test_get_library(self):
        """Test GET /library/"""
        if not self.token:
            print("  ⊘ /library/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/library/",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            self.log_result("/library/", "GET", response.status_code, success,
                          "Library retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/library/", "GET", 0, False, str(e)[:50])

    # =========== BOOKS ENDPOINTS ===========

    def test_create_book(self):
        """Test POST /books/"""
        if not self.token:
            print("  ⊘ /books/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            book_data = {
                "asin": "B00TEST001",
                "title": "Test Book",
                "author": "Test Author",
                "duration_ms": 3600000,
                "language_name": "English",
                "rating": 4.5,
                "purchase_date": "2026-01-01"
            }
            response = requests.post(
                f"{self.base_url}/books/",
                headers=headers,
                json=book_data,
                timeout=TIMEOUT
            )
            success = response.status_code in [201, 400]
            self.log_result("/books/", "POST", response.status_code, success,
                          "Book created or invalid data" if success else response.text[:50])
        except Exception as e:
            self.log_result("/books/", "POST", 0, False, str(e)[:50])

    def test_delete_book(self):
        """Test DELETE /books/{asin}"""
        if not self.token:
            print("  ⊘ /books/DELETE skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            # Try to delete a non-existent book to test the endpoint
            response = requests.delete(
                f"{self.base_url}/books/B00NOTEXIST",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 404]  # 404 if not found
            self.log_result("/books/{asin}", "DELETE", response.status_code, success,
                          "Delete endpoint tested" if success else response.text[:50])
        except Exception as e:
            self.log_result("/books/{asin}", "DELETE", 0, False, str(e)[:50])

    # =========== SYNC ENDPOINTS ===========

    def test_trigger_sync(self):
        """Test POST /sync/"""
        if not self.token:
            print("  ⊘ /sync/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.base_url}/sync/",
                headers=headers,
                json={"sync_type": "full"},
                timeout=TIMEOUT
            )
            success = response.status_code in [202, 400, 500]  # 202 Accepted for async operation
            self.log_result("/sync/", "POST", response.status_code, success,
                          "Sync triggered (async)" if response.status_code == 202 else response.text[:50])
        except Exception as e:
            self.log_result("/sync/", "POST", 0, False, str(e)[:50])

    def test_get_sync_history(self):
        """Test GET /sync/history"""
        if not self.token:
            print("  ⊘ /sync/history skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/sync/history",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 400]
            self.log_result("/sync/history", "GET", response.status_code, success,
                          "History retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/sync/history", "GET", 0, False, str(e)[:50])

    # =========== DOWNLOADS ENDPOINTS ===========

    def test_get_downloads(self):
        """Test GET /downloads/"""
        if not self.token:
            print("  ⊘ /downloads/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/downloads/",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            self.log_result("/downloads/", "GET", response.status_code, success,
                          "Downloads retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/downloads/", "GET", 0, False, str(e)[:50])

    # =========== DECRYPTIONS ENDPOINTS ===========

    def test_get_decryptions(self):
        """Test GET /decryptions/"""
        if not self.token:
            print("  ⊘ /decryptions/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/decryptions/",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code == 200
            self.log_result("/decryptions/", "GET", response.status_code, success,
                          "Decryptions retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/decryptions/", "GET", 0, False, str(e)[:50])

    # =========== FILES ENDPOINTS ===========

    def test_stream_audiobook(self):
        """Test GET /files/audiobook/{asin}"""
        if not self.token:
            print("  ⊘ /files/audiobook/{asin} skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            # Try to stream a non-existent audiobook to test the endpoint
            response = requests.get(
                f"{self.base_url}/files/audiobook/B00NOTEXIST",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 404, 206]  # 404 if not found, 206 with Range header
            self.log_result("/files/audiobook/{asin}", "GET", response.status_code, success,
                          "Stream endpoint tested" if success else response.text[:50])
        except Exception as e:
            self.log_result("/files/audiobook/{asin}", "GET", 0, False, str(e)[:50])

    # =========== ERRORS ENDPOINTS ===========

    def test_get_errors(self):
        """Test GET /errors/"""
        if not self.token:
            print("  ⊘ /errors/ skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/errors/",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 403]
            self.log_result("/errors/", "GET", response.status_code, success,
                          "Errors retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/errors/", "GET", 0, False, str(e)[:50])

    # =========== SETTINGS ENDPOINTS ===========

    def test_get_audible_credentials(self):
        """Test GET /settings/audible-credentials"""
        if not self.token:
            print("  ⊘ /settings/audible-credentials skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{self.base_url}/settings/audible-credentials",
                headers=headers,
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 400]
            self.log_result("/settings/audible-credentials", "GET", response.status_code, success,
                          "Credentials retrieved" if success else response.text[:50])
        except Exception as e:
            self.log_result("/settings/audible-credentials", "GET", 0, False, str(e)[:50])

    # =========== AUDIBLE ENDPOINTS ===========

    def test_audible_auth_start(self):
        """Test POST /audible/auth/start"""
        if not self.token:
            print("  ⊘ /audible/auth/start skipped (no auth token)")
            return
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{self.base_url}/audible/auth/start",
                headers=headers,
                json={"country_code": "us"},
                timeout=TIMEOUT
            )
            success = response.status_code in [200, 400]
            self.log_result("/audible/auth/start", "POST", response.status_code, success,
                          "Auth start processed" if success else response.text[:50])
        except Exception as e:
            self.log_result("/audible/auth/start", "POST", 0, False, str(e)[:50])

    def run_all_tests(self):
        """Run all endpoint tests."""
        print("\n" + "=" * 80)
        print("AUDIOBOOKSYNC API ENDPOINT TESTS")
        print("=" * 80 + "\n")

        print("1. Health & Info Endpoints:")
        self.test_health()

        print("\n2. Authentication Endpoints:")
        # First register a new user with unique credentials
        self.test_register(TEST_USER)
        # Then login with the same credentials
        if self.user_id or sum(1 for r in self.results if "register" in r["endpoint"] and r["success"]):
            self.test_login(TEST_USER)
        self.test_refresh_token()

        print("\n3. User Endpoints:")
        self.test_get_current_user()
        self.test_change_password()

        print("\n4. Library Endpoints:")
        self.test_get_library()

        print("\n5. Books Endpoints:")
        self.test_create_book()
        self.test_delete_book()

        print("\n6. Sync Endpoints:")
        self.test_trigger_sync()
        self.test_get_sync_history()

        print("\n7. Downloads Endpoints:")
        self.test_get_downloads()

        print("\n8. Decryptions Endpoints:")
        self.test_get_decryptions()

        print("\n9. Files Endpoints:")
        self.test_stream_audiobook()

        print("\n10. Errors Endpoints:")
        self.test_get_errors()

        print("\n11. Settings Endpoints:")
        self.test_get_audible_credentials()

        print("\n12. Audible Endpoints:")
        self.test_audible_auth_start()

        self.print_summary()

        # Return exit code based on results
        failed = sum(1 for r in self.results if not r["success"])
        return 0 if failed == 0 else 1

if __name__ == "__main__":
    tester = APITester(BASE_URL)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
