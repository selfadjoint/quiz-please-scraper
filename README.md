# Quiz Please Stats - AWS Lambda Deployment

This project automates the deployment of a Python-based AWS Lambda function to process and transform
the [Quiz Please](https://quizplease.ru/) games data, storing the results in Google Sheets. The architecture is designed
to stay within the AWS Free Tier, making it cost-effective for personal use.

## Prerequisites

Before deploying this project, ensure the following prerequisites are met:

- AWS Account: You will need an AWS account. If you don't have one, you can sign up for
  the [AWS Free Tier](https://aws.amazon.com/free/).
- AWS CLI: The AWS Command Line Interface should be installed and configured with your AWS
  credentials. [AWS CLI Installation Guide](https://aws.amazon.com/cli/).
- Docker: Required for building the Lambda function's Docker
  image. [Docker Installation Guide](https://docs.docker.com/get-docker/).
- Terraform: Used for deploying AWS resources. [Terraform Installation Guide](https://www.terraform.io/downloads).
- jq: A lightweight and flexible command-line JSON
  processor. [jq Installation Guide](https://jqlang.github.io/jq/download/).
- Google Service Account: A Google Cloud Platform service account with permissions to access Google
  Sheets. [Creating and Managing Service Accounts](https://cloud.google.com/iam/docs/service-accounts-create).
- Google Service Account Credentials File: A JSON file containing your service account's credentials.

## Configuration

Create a `terraform.tfvars` file in the `terraform` directory with the following variables and any other variables to overwrite the default values from `variables.tf` if needed:
```hcl
aws_credentials_file    = "~/.aws/credentials"
aws_profile             = "your_aws_profile"
aws_account_id          = "12334556"                
notification_email      = "test@test.test"          
google_credentials_file = "google_credentials.json" 
```
Create a file named `backend.hcl` inside the `terraform` folder with content similar to:

```hcl
bucket       = "your-tf-state-bucket"                  # Replace with your S3 bucket name
key          = "your-resource-name/terraform.tfstate"  # Adjust as needed
region       = "us-east-1"                             # Your AWS region
profile      = "your_aws_profile"                      # The AWS CLI profile to use
encrypt      = true
use_lockfile = true
```

## Python Script

The core functionality of this project is driven by a [Python script](src/main.py) which:

- Scrapes quiz data from a specified URL.
- Transforms the data and prepares it for Google Sheets.
- Utilizes `gspread` to interact with Google Sheets, loading data efficiently.
- Leverages AWS SSM Parameter Store for securely storing Google credentials.
- Implements error handling and logging for monitoring and debugging purposes.

This script is packaged and deployed as an AWS Lambda function, set to execute on a daily schedule using AWS
EventBridge.

## Architecture

The project uses AWS Lambda, AWS SNS for error notifications, AWS CloudWatch for monitoring, and an EventBridge rule for
daily script execution. Data is stored and processed in Google Sheets.

## Deployment

Deployment is automated via a script, `deploy.sh`, which encompasses the following steps:

1. **Build and Push Docker Image:** The script runs `src/image_push.sh` to build the Docker image and push it to an AWS
   ECR repository.

2. **Terraform Deployment:** The script then executes the Terraform commands to deploy the necessary AWS resources,
   including the Lambda function, IAM roles, CloudWatch event rule, and SNS topic for error notifications.

To deploy:

- Ensure all prerequisites are installed and properly configured.
- Run the deployment script:
  ```bash
  ./deploy.sh

3. **Monitor and Test:** After deployment, you can monitor the Lambda function in the AWS Console. Test the function to
   ensure it's processing and updating data as expected.

## Staying Within the AWS Free Tier

This project is designed to operate within the AWS Free Tier limits. However, it's essential to monitor your AWS usage
to avoid unexpected charges, especially if your usage scales up.

## Notes

- Ensure all prerequisites are installed and properly configured before deploying.
- The provided Terraform script and Docker build script are tested on MacOS 14. Adjustments may be required for other
  operating systems.

## License

This project is released under the [MIT License](LICENSE).

## What to Do with the Data

Whatever you want :) Here is the Tableau dashboard (in Russian) I created using the data scraped by this
script: [Quiz Please Yerevan Dashboard](https://public.tableau.com/app/profile/dannyviz/viz/QuizPleaseYerevan/Teamstats).
