mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }
}

run "default_configuration" {
  command = plan

  variables {
    container_image = "public.ecr.aws/docker/library/nginx:stable-alpine"
  }

  assert {
    condition     = aws_ecs_express_gateway_service.app.health_check_path == "/health"
    error_message = "The service must use the FastAPI health endpoint by default."
  }

  assert {
    condition     = aws_ecs_express_gateway_service.app.cpu == "256" && aws_ecs_express_gateway_service.app.memory == "512"
    error_message = "The default task must use the smallest supported Fargate size."
  }

  assert {
    condition     = aws_cloudwatch_log_group.app.retention_in_days == 30
    error_message = "Application logs must expire after 30 days by default."
  }

  assert {
    condition     = aws_ecs_express_gateway_service.app.wait_for_steady_state
    error_message = "Terraform must wait for the ECS service to become steady."
  }

  assert {
    condition = one([
      for item in aws_ecs_express_gateway_service.app.primary_container[0].environment : item.value
      if item.name == "PORT"
    ]) == "80"
    error_message = "The container PORT setting must track container_port."
  }
}

run "reject_invalid_health_path" {
  command = plan

  variables {
    container_image   = "public.ecr.aws/docker/library/nginx:stable-alpine"
    health_check_path = "health"
  }

  expect_failures = [var.health_check_path]
}

run "reject_invalid_fargate_size" {
  command = plan

  variables {
    container_image = "public.ecr.aws/docker/library/nginx:stable-alpine"
    cpu             = 256
    memory          = 4096
  }

  expect_failures = [aws_ecs_express_gateway_service.app]
}
