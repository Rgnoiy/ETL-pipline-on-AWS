import boto3


def sqs_delete_from_queue(receipt):
    sqs = boto3.client('sqs')
    sqs.delete_message(
    QueueUrl='https://sqs.eu-west-1.amazonaws.com/370445109106/team4-queue2',
    ReceiptHandle=receipt
    )
    print('Deleted message from SQS queue.')
    

def get_db_credentials(credential_name):
        ssm = boto3.client("ssm")
        response = ssm.get_parameter(Name=credential_name)
        creds_string = response["Parameter"]["Value"]
        db, user, password, host, port = creds_string.split(",")
        
        return db, user, password, host, port