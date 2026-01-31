print("Importing os, sys...")
import os
import sys
print("Importing FastAPI...")
from fastapi import FastAPI
print("Importing devops_portal.main...")
try:
    from devops_portal.main import app
    print("Successfully imported app")
except Exception as e:
    print(f"Failed to import app: {e}")
print("Importing models...")
try:
    from devops_collector.models.base_models import Base, User
    print("Successfully imported models")
except Exception as e:
    print(f"Failed to import models: {e}")
print("Done")
