terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.26"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region                   = var.aws_region
  shared_credentials_files = var.aws_credentials_file
  profile                  = var.aws_profile
}


# SSM Parameter for Google Credentials
resource "aws_ssm_parameter" "google_credentials" {
  name  = "/quizgame/google_credentials"
  type  = "SecureString"
  value = file(var.google_credentials_file) # Path to your credentials file

  tags = var.tags
}

# Lambda Role and Policy
resource "aws_iam_role" "lambda_execution_role" {
  name = var.resource_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
      },
    ],
  })
}

resource "aws_iam_role_policy" "lambda_execution_role_policy" {
  name = var.resource_name
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "ssm:GetParameter"
        ],
        Effect   = "Allow",
        Resource = aws_ssm_parameter.google_credentials.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ],
        Effect   = "Allow",
        Resource = "*" # Adjust this to restrict to specific ECR repositories if necessary
      }
    ],
  })
}


# Lambda Function
resource "aws_lambda_function" "game_stats" {
  description   = "Parse quiz game data, process it, and store it in a Google Sheet"
  function_name = var.resource_name
  role          = aws_iam_role.lambda_execution_role.arn
  package_type  = "Image"
  timeout       = 300
  memory_size   = 256

  image_uri = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${lower(var.resource_name)}:${var.image_tag}"

  tags = var.tags
}

resource "aws_lambda_permission" "allow_execution" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.game_stats.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule_rule.arn
}

# CloudWatch Event Rule
resource "aws_cloudwatch_event_rule" "schedule_rule" {
  name                = var.resource_name
  description         = "Extract, transform and load quiz game stats"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule_rule.name
  target_id = var.resource_name
  arn       = aws_lambda_function.game_stats.arn
}

# SNS Topic for Error Notifications
resource "aws_sns_topic" "lambda_error_notifications" {
  name = var.resource_name
  tags = var.tags
}

resource "aws_sns_topic_subscription" "lambda_error_email" {
  topic_arn = aws_sns_topic.lambda_error_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# CloudWatch Alarm for Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = var.resource_name
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors Lambda errors"
  alarm_actions       = [aws_sns_topic.lambda_error_notifications.arn]
  dimensions = {
    FunctionName = aws_lambda_function.game_stats.function_name
  }
}
