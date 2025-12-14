
import sys
import os
import unittest
import importlib

# Add project root to path
# Assuming this script is in scripts/ and project root is one level up
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Project root added to path: {project_root}")

class TestP0Fixes(unittest.TestCase):

    def test_unified_base(self):
        """Verify that all modules use the same Base instance (P0-3)."""
        print("\nTesting Unified Base...")
        from devops_collector.models.base_models import Base as BaseRoot
        from devops_collector.plugins.gitlab.models import Base as BaseGitLab
        from devops_collector.plugins.sonarqube.models import Base as BaseSonar
        
        self.assertIs(BaseRoot, BaseGitLab, "GitLab plugin is using a different Base instance")
        self.assertIs(BaseRoot, BaseSonar, "SonarQube plugin is using a different Base instance")
        print("[PASS] Base Uniformity Check Passed")

    def test_worker_imports(self):
        """Verify that Workers can be imported and use unified models (P0-1, P0-2)."""
        print("\nTesting Worker Imports...")
        
        # Test GitLab Worker
        try:
            from devops_collector.plugins.gitlab import worker as gitlab_worker_module
            print("[PASS] GitLab worker module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import GitLab worker: {e}")
            
        # Test SonarQube Worker
        try:
            from devops_collector.plugins.sonarqube import worker as sonarqube_worker_module
            print("[PASS] SonarQube worker module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import SonarQube worker: {e}")

    def test_circular_imports(self):
        """Verify that no circular imports occur during standard usage."""
        print("\nTesting Circular Imports...")
        # Reloading modules can sometimes catch initialization circular deps
        try:
            import devops_collector.models
            import devops_collector.plugins.gitlab
            import devops_collector.plugins.sonarqube
            # import devops_collector.plugin_loader # Does not exist
            from devops_collector.core import PluginRegistry
            print("[PASS] Core modules imported without circular dependency errors")
        except ImportError as e:
            self.fail(f"Circular import detected: {e}")

    def test_is_virtual_field(self):
        """Verify that User model has is_virtual field (P1-1)."""
        print("\nTesting User Model Field (is_virtual)...")
        from devops_collector.models import User
        
        # Check if the column exists in the ORM definition
        self.assertTrue(hasattr(User, 'is_virtual'), "User model missing 'is_virtual' field")
        print("[PASS] User.is_virtual field exists")

if __name__ == '__main__':
    unittest.main()
