terraform {
  required_version = ">= 0.13"
}
# ------------------------------------------------------------------------------
# CONFIGURE OUR AWS CONNECTION AND STS ASSUME ROLE
# ------------------------------------------------------------------------------
provider "aws" {
  region = "eu-west-1"
  # assume_role {
  #   profile = ""
  #   role_arn = ""
  #   session_name = ""
  # }
}
# ------------------------------------------------------------------------------
# CONFIGURE REMOTE STATE
# ------------------------------------------------------------------------------
terraform {
  backend "s3" {
    bucket = "team4-delon7-tf-state"
    key    = "hisham-terraform.tfstate"
    region = "eu-west-1"
    # role_arn = ""
    # session_name = ""
  }
}

################################################################################
# Lambda role
################################################################################
resource "aws_iam_role" "lambda_function_role" {
  name               = "team4-lambda-etl-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}
resource "aws_iam_role_policy_attachment" "lambda_execution_role" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy_attachment" "redshift_full_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRedshiftFullAccess"
}
resource "aws_iam_role_policy_attachment" "lamdba_vpc_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ################################################################################
# # 1st Lambda function, layers
# ################################################################################
resource "aws_lambda_function" "lambda_transform" {
  filename      = "src.zip"
  function_name = "team4stack-LambdaFunction"
  handler       = "src.lambda_function.lambda_handler"
  role          =  aws_iam_role.lambda_function_role.arn
  runtime       = "python3.8"
  memory_size   = 512
  timeout       = 30
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-python38-aws-psycopg2:1",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-pandas:4",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-SQLAlchemy:3"
  ]
  source_code_hash = filebase64sha256("src.zip")
  # vpc_config {
  #   subnet_ids = [
  #     "${var.subnet_one_id}",
  #     "${var.subnet_two_id}"
  #   ]
  #   security_group_ids = ["${var.security_group_id}"]
  # }
}
#-------------------------------------------------------------
### integration of s3 bucket and sqs

# resource "aws_lambda_permission" "allow_bucket" {
# statement_id  = "AllowExecutionFromS3Bucket"
# action        = "lambda:InvokeFunction"
# function_name = aws_lambda_function.lambda_etl.arn
# principal     = "s3.amazonaws.com"
# source_arn    = aws_s3_bucket.transactions_bucket.arn
# }



### Setting up SQS
resource "aws_sqs_queue" "queue" {
  name = "team4-queue1"
  policy = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:eu-west-1:370445109106:team4-queue1"
    }
  ]
}
EOF
}

### s3 bucket
resource "aws_s3_bucket" "transactions_bucket" {
  bucket = "team4-store-transactions-data-raw"
}

### S3 event notification
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.transactions_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  } 
}

# Event source from sqs
resource "aws_lambda_event_source_mapping" "sqs_lambda_trigger" {
  event_source_arn = aws_sqs_queue.queue.arn
  function_name    = aws_lambda_function.lambda_transform.arn
  batch_size = 1
} 


#######################################################################


resource "aws_lambda_function" "lambda_load" {
  filename      = "src_load.zip"
  function_name = "team4-lambda-load"
  handler       = "src.lambda_function.lambda_handler"
  role          =  aws_iam_role.lambda_function_role.arn
  runtime       = "python3.8"
  memory_size   = 512
  timeout       = 30
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-python38-aws-psycopg2:1",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-pandas:4",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-SQLAlchemy:3"
  ]
  source_code_hash = filebase64sha256("src_load.zip")
}

### Setting up SQS
resource "aws_sqs_queue" "queue2" {
  name = "team4-queue2"
  policy = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:eu-west-1:370445109106:team4-queue2"
    }
  ]
}
EOF
}

### s3 bucket
resource "aws_s3_bucket" "load_bucket" {
  bucket = "team4-transformed-data"
}

### S3 event notification
resource "aws_s3_bucket_notification" "bucket_notification2" {
  bucket = aws_s3_bucket.load_bucket.id

  queue {
    queue_arn     = aws_sqs_queue.queue2.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  } 
}

# Event source from sqs
resource "aws_lambda_event_source_mapping" "sqs_lambda_trigger2" {
  event_source_arn = aws_sqs_queue.queue2.arn
  function_name    = aws_lambda_function.lambda_load.arn
  batch_size = 1
} 



