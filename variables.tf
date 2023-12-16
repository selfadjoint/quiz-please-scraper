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

variable "notification_email" {
  type = string
}

