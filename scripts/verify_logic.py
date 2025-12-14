import sys
import os
import time

# Add current dir to path
sys.path.append(os.getcwd())

def test_imports():
    print("Testing imports...")
    try:
        from devops_collector.models import Project, Commit
        from devops_collector.config import Config
        from devops_collector.core.base_client import RateLimiter
        from devops_collector.mq import MessageQueue
        from devops_collector.scheduler import main as scheduler_main
        # Worker doesn't have a main function exposed in the same way, adapting
        from devops_collector.plugins.gitlab.worker import GitLabWorker
        print("Imports successful.")
    except Exception as e:
        print(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_rate_limiter():
    print("Testing Rate Limiter...")
    from devops_collector.core.base_client import RateLimiter
    
    # Allow 5 requests per second
    limiter = RateLimiter(5)
    
    start = time.time()
    for i in range(10):
        limiter.wait_for_token()
    end = time.time()
    
    duration = end - start
    print(f"Taken {duration:.2f}s for 10 requests (limit 5/s)")
    
    # Should take at least 1.8s approx (since first 5 are instant, next 5 wait)
    # Actually, if token bucket starts full:
    # 5 tokens consumed immediately.
    # 6th token needs 0.2s
    # 7th token needs 0.2s ...
    # Total wait for 5 more tokens = 1.0s
    if duration < 0.8: 
        print(f"Rate limiter too fast! {duration}s")
        sys.exit(1)
    print("Rate limiter passed.")

def test_sonarqube_components():
    print("Testing SonarQube Components...")
    try:
        from devops_collector.plugins.sonarqube.client import SonarQubeClient
        from devops_collector.plugins.sonarqube.worker import SonarQubeWorker
        
        # Test basic instantiation (without connecting)
        client = SonarQubeClient("https://example.com", "token")
        assert client.base_url == "https://example.com/api"
        print("[PASS] SonarQubeClient instantiated successfully")
        
    except Exception as e:
        print(f"SonarQube component test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_imports()
    test_rate_limiter()
    test_sonarqube_components()
