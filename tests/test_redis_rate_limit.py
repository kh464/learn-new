from app.runtime_ops import RedisRateLimiter


class FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expirations = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_redis_rate_limiter_tracks_counts_with_prefix() -> None:
    client = FakeRedis()
    limiter = RedisRateLimiter(
        requests=2,
        window_seconds=30,
        client=client,
        key_prefix="learn-new:test",
    )

    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is True
    assert limiter.allow("127.0.0.1") is False
    assert client.expirations["learn-new:test:127.0.0.1"] == 30
