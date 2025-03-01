# Quiz Please Stats Scraper

This project automates the deployment of a Python-based AWS Lambda function to process and transform
the [Quiz Please](https://quizplease.ru/) games data, storing the results in Google Sheets. The architecture is designed
to stay within the AWS Free Tier, making it cost-effective for personal use.

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Python Script](#python-script)
- [Architecture](#architecture)
- [What to Do with the Data](#what-to-do-with-the-data)
- [Clean Up](#clean-up)

## Project Structure

```plaintext
├── src
│   ├── main.py                # Lambda function code
│   ├── requirements.txt       # Python dependency definitions
│   └── (other source files or folders)
└── terraform
    ├── main.tf                # Terraform configuration
    ├── variables.tf           # Input variables
    ├── backend.hcl            # Backend configuration (not committed; see below)
    └── (other Terraform files)
├── README.md
```

## Prerequisites

Before you begin, ensure you have the following installed:

- [AWS CLI](https://aws.amazon.com/cli/)
- [Terraform](https://www.terraform.io/)
- [Python 3.11+](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)
- [Google Service Account](https://cloud.google.com/iam/docs/service-accounts-create) with a JSON file containing your service account's credentials.

## Setup

### 1. Clone the repository:

   ```bash
   git clone https://github.com/your-repo/quiz-plese-reg.git
   cd quiz-please-reg

### 2. Install Python Dependencies
The dependencies are not committed to the repository. To install them into the src folder, run:
```bash
pip install --upgrade --target ./src -r src/requirements.txt
```
This command installs all required Python packages into the src directory so that they are included in the Lambda deployment package.

### 3. Configure the Terraform Backend and Variables
Terraform uses an S3 backend for state storage. Since sensitive information should not be committed to the repository, create a separate backend configuration file.

Create a file named `backend.hcl` inside the `terraform` folder with content similar to:

```hcl
bucket       = "your-tf-state-bucket"                  # Replace with your S3 bucket name
key          = "your-resource-name/terraform.tfstate"  # Adjust as needed
region       = "us-east-1"                             # Your AWS region
profile      = "your_aws_profile"                      # The AWS CLI profile to use
encrypt      = true
use_lockfile = true
```
**Create a `terraform.tfvars` file with the necessary variables. Example**:

```hcl
aws_profile                = "default"
google_credentials_file    = "path/to/google_credentials.json"
notification_email         = "d5YQZ@example.com"
```

### 4. Initialize Terraform
Change to the terraform directory and initialize Terraform using the backend configuration:
```bash
cd terraform
terraform init -backend-config=backend.hcl
```
This command sets up the backend and downloads required providers.

### 5. Review and Apply the Terraform Configuration
First, run a plan to see the changes that Terraform will apply:
```bash
terraform plan
```

If everything looks correct, deploy the resources with:
```bash
terraform apply
```
Confirm the apply action when prompted.

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


## What to Do with the Data

Whatever you want :) Here is the Tableau dashboard (in Russian) I created using the data scraped by this
script: [Quiz Please Yerevan Dashboard](https://public.tableau.com/app/profile/dannyviz/viz/QuizPleaseYerevan/Teamstats).

## Clean Up
To remove all resources created by Terraform, run:
```bash
terraform destroy
```
This will tear down the deployed AWS resources.
