# Deployment notes

## Local and single-node

`compose.yaml` runs the API, analyst workbench, SQLite evidence database, and local report/raw-source store. It fails closed unless `AIFACTORY_API_KEY` and a real `AIFACTORY_SEC_USER_AGENT` contact are set. Model and optional source credentials are passed from the environment without defaults containing secrets.

## Kubernetes

The quarterly CronJob expects:

- Image `your-registry/aifactory-research:0.1.0` replaced with the deployed image.
- Secret `aifactory-secrets` containing the environment configuration.
- Persistent volume claim `aifactory-data`.

For more than one writer, replace SQLite with PostgreSQL before deploying multiple worker replicas. The reference database class intentionally remains SQLite so local results are reproducible without infrastructure.

Install `.[production,otel]` for the declared PostgreSQL, S3/MinIO, Temporal, Redis, analytics, vector-retrieval, and telemetry libraries. Those extras are an implementation target, not an automatic storage migration; introduce repository/object-store adapters and database migrations before scaling.

## Production checklist

- Private container registry and signed image.
- Dependency and image vulnerability scanning.
- SBOM retained with the release.
- Network policy limiting egress to approved sources and model gateway.
- SSO/RBAC in front of the analyst UI and API.
- Secret manager integration; no plain Kubernetes secrets in Git.
- PostgreSQL backups and point-in-time recovery.
- Object-storage immutability and lifecycle policy.
- OpenTelemetry collector plus log/metric retention.
- Model and source data-processing agreements.
- Load, recovery, and prompt-injection tests.
- Analyst and methodology-owner sign-off.
