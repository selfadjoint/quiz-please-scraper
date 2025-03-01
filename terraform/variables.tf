variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_credentials_file" {
  type    = list(string)
  default = ["$HOME/.aws/credentials"]
}

variable "aws_profile" {
  type    = string
  default = "default"
}

variable "google_credentials_file" {
  type    = string
  default = "google_credentials.json"
}

variable "tags" {
  type = map(string)
  default = {
    Name    = "QuizPleaseStats"
    Project = "QuizPlease"
  }
}

variable "notification_email" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "resource_name" {
  description = "The prefix for all resource names"
  type        = string
  default     = "QuizPleaseStats"
}
