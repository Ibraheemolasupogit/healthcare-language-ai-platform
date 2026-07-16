# Local Security Boundaries

The API and dashboard default to localhost. No production authentication or authorization is claimed. The implementation is read-only and synthetic-only, with no public exposure, no remote telemetry, no cloud connections, and no real patient data.

Docker examples must bind published ports to `127.0.0.1` on the host. Binding to `0.0.0.0` is only acceptable inside a local container when host publishing remains loopback-bound.
