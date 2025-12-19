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
        # 每秒 10 个令牌
        limiter = RateLimiter(rate_limit=10)
        
        # 初始应满
        self.assertEqual(int(limiter.tokens), 10)
        
        # 消耗 5 个
        for _ in range(5):
            self.assertTrue(limiter.get_token())
        
        self.assertLess(limiter.tokens, 6)
        
        # 等待 0.5 秒，应恢复约 5 个令牌
        time.sleep(0.5)
        limiter.get_token()  # 触发更新
        self.assertGreater(limiter.tokens, 9)

    def test_wait_for_token_blocking(self):
        """测试 wait_for_token 的延迟阻塞。"""
        # 设置极低的频率方便测试：每秒 1 个
        limiter = RateLimiter(rate_limit=1)
        
        # 先取走默认的一个
        self.assertTrue(limiter.get_token())
        
        start_time = time.time()
        # 再次获取，此时令牌桶为空，应阻塞约 1 秒
        # (RateLimiter.wait_for_token 内部循环 sleep 0.1)
        limiter.wait_for_token()
        end_time = time.time()
        
        duration = end_time - start_time
        # 考虑到填充速度和循环频率，时间应在 0.9 - 1.2s 之间
        self.assertGreaterEqual(duration, 0.8)


if __name__ == '__main__':
    unittest.main()
