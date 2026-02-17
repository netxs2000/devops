"""单元测试：RateLimiter

验证 RateLimiter (令牌桶算法) 的限流准确性。
"""
import unittest
import time
from devops_collector.core.base_client import RateLimiter

class TestRateLimiter(unittest.TestCase):
    """RateLimiter 限流逻辑测试类。"""

    def test_token_bucket_refill(self):
        """测试令牌桶的自动填充逻辑。"""
        limiter = RateLimiter(rate_limit=10)
        self.assertEqual(int(limiter.tokens), 10)
        for _ in range(5):
            self.assertTrue(limiter.get_token())
        self.assertLess(limiter.tokens, 6)
        time.sleep(0.5)
        limiter.get_token()
        self.assertGreater(limiter.tokens, 9)

    def test_wait_for_token_blocking(self):
        """测试 wait_for_token 的延迟阻塞。"""
        limiter = RateLimiter(rate_limit=1)
        self.assertTrue(limiter.get_token())
        start_time = time.time()
        limiter.wait_for_token()
        end_time = time.time()
        duration = end_time - start_time
        self.assertGreaterEqual(duration, 0.8)
if __name__ == '__main__':
    unittest.main()