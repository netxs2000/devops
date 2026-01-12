import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

print("Attempting to import devops_portal.main...")
try:
    from devops_portal import main
    print("Successfully imported devops_portal.main")
except Exception as e:
    print(f"Failed to import devops_portal.main: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import devops_portal.routers.test_management_router...")
try:
    from devops_portal.routers import test_management_router
    print("Successfully imported devops_portal.routers.test_management_router")
except Exception as e:
    import traceback
    traceback.print_exc()
