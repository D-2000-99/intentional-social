"""Custom Prometheus metrics for monitoring application performance."""
from prometheus_client import Counter, Histogram, Gauge

# Request counters
feed_requests_total = Counter(
    'feed_requests_total',
    'Total number of feed requests'
)

digest_requests_total = Counter(
    'digest_requests_total',
    'Total number of digest requests'
)

post_creations_total = Counter(
    'post_creations_total',
    'Total number of posts created'
)

post_deletions_total = Counter(
    'post_deletions_total',
    'Total number of posts deleted'
)

connection_requests_total = Counter(
    'connection_requests_total',
    'Total number of connection requests sent'
)

connection_accepts_total = Counter(
    'connection_accepts_total',
    'Total number of connection requests accepted'
)

# Latency histograms
feed_latency_seconds = Histogram(
    'feed_latency_seconds',
    'Feed endpoint latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

digest_latency_seconds = Histogram(
    'digest_latency_seconds',
    'Digest endpoint latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

post_creation_latency_seconds = Histogram(
    'post_creation_latency_seconds',
    'Post creation latency in seconds',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

db_query_latency_seconds = Histogram(
    'db_query_latency_seconds',
    'Database query latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

s3_operation_latency_seconds = Histogram(
    's3_operation_latency_seconds',
    'S3 operation latency in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

# Gauges
active_connections_gauge = Gauge(
    'active_connections_total',
    'Total number of active connections in the system'
)

posts_total_gauge = Gauge(
    'posts_total',
    'Total number of posts in the system'
)

users_total_gauge = Gauge(
    'users_total',
    'Total number of users in the system'
)
