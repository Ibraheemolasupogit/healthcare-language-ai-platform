# Local Rate Limiting

The read-only query API includes an in-memory, thread-safe local rate limiter.
It is enabled by configuration and returns a structured `429` error when a
client exceeds the configured window.

The limiter protects local demos from accidental repeated calls. It is not
distributed and is not a production abuse-prevention system.
