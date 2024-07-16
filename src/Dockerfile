FROM public.ecr.aws/lambda/python:3.11

# Install necessary OS packages
RUN yum install -y gcc libxml2-devel libxslt-devel && yum clean all

# Copy function code and requirements.txt
COPY main.py requirements.txt ${LAMBDA_TASK_ROOT}/

# Install the specified Python packages
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Set the CMD to your handler (this is the function AWS Lambda will call)
CMD [ "main.lambda_handler" ]
