#!/bin/bash

# Function to extract variable value from terraform.tfvars
extract_tfvars_value() {
  grep "^$1 =" ../terraform.tfvars | cut -d '=' -f2 | xargs
}

# Function to extract variable default value from variables.tf
extract_default_value() {
  grep -E "^variable \"$1\" \{" -A 2 ../variables.tf | grep 'default =' | cut -d '=' -f2 | xargs
}

# Function to get variable value
get_variable_value() {
  local variable_name=$1
  local value=$(extract_tfvars_value "$variable_name")

  if [ -z "$value" ]; then
    value=$(extract_default_value "$variable_name")
  fi

  echo $value
}

# Variables to look for
region=$(get_variable_value "aws_region")
aws_account_id=$(get_variable_value "aws_account_id")
repository_name=$(get_variable_value "repository_name")
image_name=$(get_variable_value "image_name")
image_tag=$(get_variable_value "image_tag")

# Check if variables are empty
if [ -z "$region" ] || [ -z "$aws_account_id" ] || [ -z "$repository_name" ]; then
  echo "Error: One or more required variables are not set."
  exit 1
fi

# Function to check if the repository already exists
repository_exists() {
  aws ecr describe-repositories --region $region | grep -q "\"repositoryName\": \"$repository_name\""
  return $?
}

# AWS ECR and Docker commands with variables
docker logout public.ecr.aws
aws ecr get-login-password --region $region | docker login --username AWS \
--password-stdin $aws_account_id.dkr.ecr.$region.amazonaws.com

# Check if repository exists before creating
if repository_exists; then
  echo "Repository $repository_name already exists in AWS ECR."
else
  aws ecr create-repository --repository-name $repository_name --region $region \
   --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
  echo "Repository $repository_name created in AWS ECR."
fi

# Build Docker image
docker build --platform linux/amd64 -t $image_name:$image_tag .

# Tag the Docker image
docker tag $repository_name:$image_tag $aws_account_id.dkr.ecr.$region.amazonaws.com/$repository_name:$image_tag

# Push the Docker image
docker push $aws_account_id.dkr.ecr.$region.amazonaws.com/$repository_name:$image_tag
echo "Docker image pushed to $repository_name repository in AWS ECR."