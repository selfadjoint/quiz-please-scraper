#!/bin/bash

# Stop on first error
set -e

# Run the image push script
echo "Running the Docker image push script..."
cd "src/"
bash "image_push.sh"

# Initialize Terraform (if needed)
echo "Initializing Terraform..."
cd "../terraform/"
terraform init

# Apply the Terraform script
echo "Applying Terraform script..."
terraform apply

echo "Deployment complete."
