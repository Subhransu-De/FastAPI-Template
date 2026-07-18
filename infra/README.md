# Deployment options

Each directory below is an independent Terraform root. Choose one deployment flavor; no flavor imports resources or modules from another directory.

| Deployment | Best for | Operations | Cost floor | Scale to zero | Status |
| --- | --- | --- | --- | --- | --- |
| [ECS Express Mode](aws-ecs-express/README.md) | AWS-native container deployment with production-ready managed defaults | Low | Fargate plus a shared-capable ALB | No | Available |
| ECS Fargate | Explicit control over VPC, ALB, ECS, IAM, and logging | Medium | Fargate plus ALB | No | Planned in issue #67 |
| Lightsail Containers | Small applications and demos | Low | Fixed service bundle | No | Planned in issue #70 |
| Elastic Beanstalk | Docker workloads using the legacy AWS PaaS model | Medium | EC2, with optional ALB | No | Planned in issue #71 |
| Lambda Web Adapter | Low-traffic container workloads | Low | Request and duration based | Yes | Planned in issue #68 |
| Lambda with Mangum | ASGI adapter deployments behind API Gateway | Low | Request and duration based | Yes | Planned in issue #69 |

## Adoption workflow

1. Select one directory and read its prerequisites and limitations.
2. Copy its `terraform.tfvars.example` to `terraform.tfvars` and provide environment-specific values.
3. Configure a remote backend before team or production use. Local state is the template default so initial validation does not create shared AWS resources.
4. Run `make lint-infra` from the repository root, then validate the selected directory with `terraform fmt -check`, `terraform init -backend=false`, and `terraform validate`.
5. Delete the unused flavor directories. CI discovers roots dynamically, so deletion does not require matrix maintenance.

Terraform state and plan files can contain sensitive data and are excluded by the repository `.gitignore`. Commit each root's `.terraform.lock.hcl` file so provider selections and checksums remain reproducible.

Dependabot updates Terraform providers and committed lock files under `/infra/*`. It does not update the Terraform CLI version in `.github/workflows/terraform.yml`, the TFLint version shared by that workflow and `Makefile`, or the AWS ruleset version in `infra/.tflint.hcl`; review those pins together during infrastructure maintenance.
