# Amazon ECS Express Mode

This Terraform root deploys the existing FastAPI application image with Amazon ECS Express Mode. ECS creates and manages the Fargate service, HTTPS endpoint, Application Load Balancer, target groups, security groups, autoscaling, canary deployments, rollback alarms, and supporting resources.

The root remains independent: it does not reference files or Terraform modules outside this directory. The application and migration images are built from the repository root before deployment.

## Prerequisites

- Terraform 1.10 or newer and AWS provider 6.55 or newer.
- AWS credentials allowed to manage ECS, IAM roles, CloudWatch Logs, and the resources delegated through `AmazonECSInfrastructureRoleforExpressGatewayServices`.
- An immutable application image in ECR or another supported registry.
- A reachable PostgreSQL database and OIDC provider. The application requires `DATABASE_URL`, `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, and `OIDC_DOCS_CLIENT_ID` at startup.
- Either a default VPC with at least two public subnets or explicit `subnet_ids`. The default VPC path produces a public HTTPS endpoint.

Do not store AWS credentials, database URLs, tokens, or secret values in `.tf` or `.tfvars` files. The `secrets` variable accepts only Secrets Manager or SSM parameter ARNs; ECS resolves the values when the task starts.

## Build and publish the images

Authenticate Docker to ECR, create repositories if needed, and publish immutable tags or digests:

```bash
aws ecr get-login-password --region ap-south-1 \
  | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

docker build -t fastapi-template:app -f ../../Dockerfile ../..
docker tag fastapi-template:app ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/fastapi-template:COMMIT_SHA
docker push ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/fastapi-template:COMMIT_SHA

docker build -t fastapi-template:migration -f ../../Dockerfile.migration ../..
docker tag fastapi-template:migration ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/fastapi-template-migration:COMMIT_SHA
docker push ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/fastapi-template-migration:COMMIT_SHA
```

Resolve the pushed application tag to a digest and set `container_image` to the resulting `repository@sha256:...` URI for reproducible deployments.

## Configure

```bash
cp terraform.tfvars.example terraform.tfvars
```

At minimum, replace `container_image` and configure the required application settings. A typical production split is:

- `environment_variables`: non-secret OIDC URLs, client IDs, Logfire settings, and pool sizing.
- `secrets`: `DATABASE_URL` and other credentials, expressed as Secrets Manager or SSM ARNs.
- `secrets_kms_key_arns`: customer-managed KMS keys needed to decrypt those values.
- `task_role_policy_arns`: narrowly scoped policies only when application code calls AWS APIs.

The module derives the container's `PORT` environment variable from `container_port`, so changing the listener port cannot leave Uvicorn listening on the old default.

If `subnet_ids` is empty, ECS Express Mode uses the default public subnets. When supplying custom subnets, use at least two Availability Zones. Private subnets produce an internal load balancer and require a path to ECR, CloudWatch Logs, Secrets Manager or SSM, the database, and the OIDC provider through NAT or VPC endpoints.

## Validate without deploying

These commands download providers and perform static or mocked checks. They do not create AWS resources:

```bash
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
terraform test
```

The repository CI also runs TFLint with the AWS ruleset and Trivy configuration scanning.

## State for team use

Local state is the template default. Before a shared or production deployment, copy `backend.tf.example` to `backend.tf`, configure an existing versioned S3 bucket, and migrate state:

```bash
terraform init -migrate-state
```

The example uses native S3 locking with `use_lockfile = true`; it does not require a DynamoDB lock table. Restrict access to the state bucket because state can contain sensitive metadata.

## Deploy and verify

Review the proposed changes before creating resources:

```bash
terraform plan -out=tfplan
terraform apply tfplan
terraform output -raw endpoint_url
```

After the endpoint becomes active:

```bash
curl --fail --show-error --silent "$(terraform output -raw endpoint_url)/health"
```

Express Mode terminates TLS, maintains at least `min_task_count` tasks, and uses the configured target tracking metric. `wait_for_steady_state = true` keeps Terraform running until the service stabilizes.

## Database migrations

Migrations never run during FastAPI startup. Before creating or updating the service, run the migration image as a one-off ECS task with the same network path and `DATABASE_URL` secret as the application. Express Mode does not create that one-off task automatically; an external release workflow or a separately managed ECS task definition must run it and stop the release if Alembic fails.

## Destroy and residual resources

```bash
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```

The explicit IAM attachment dependencies keep the Express infrastructure policy available while ECS drains and deletes the service. Confirm deletion before removing ECR images. CloudWatch Logs and ECS-created resources should be reviewed after deletion; images pushed to ECR and an external state bucket are outside this root and remain billable until removed according to their own lifecycle policies.

## Expected cost

ECS Express Mode has no separate service fee. You pay for the underlying Fargate task, Application Load Balancer, CloudWatch usage, public IPv4 addresses, storage, and data transfer. With one 0.25-vCPU/0.5-GB task in `ap-south-1`, a short verification deployment is expected to cost only a few cents, but the ALB and continuously running task create a non-zero monthly floor. Use the AWS Pricing Calculator for the selected Region, task count, traffic, and log volume before production use.

## Required IAM behavior

The root creates three roles:

- Execution role trusted by `ecs-tasks.amazonaws.com`, with `AmazonECSTaskExecutionRolePolicy` and resource-scoped access to only the configured secret, parameter, and KMS ARNs.
- Infrastructure role trusted by `ecs.amazonaws.com`, with AWS's service-role policy for Express Gateway Services.
- Task role trusted by `ecs-tasks.amazonaws.com`; it has no permissions unless `task_role_policy_arns` is configured.

The identity running Terraform must be able to create these roles and pass the execution, infrastructure, and task roles to ECS in addition to creating the Terraform-managed ECS cluster and log group.
