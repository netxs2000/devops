import sys
import os
import pytest
import unittest

sys.path.append(os.getcwd())

if __name__ == "__main__":
    print("Running integration tests via script...")
    args = [
        "-vv",
        "--no-cov",
        "tests/integration/test_service_desk_integration.py",
        "tests/integration/test_gitlab_sync_flow.py",
        "tests/integration/auth_integration_test.py"
    ]
    pytest.main(args)
