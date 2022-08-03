import boto3
import psycopg2
import src_load.functions as f
import json

def lambda_handler(event, context):
    # db_connection--------------------------------------------------------------------------------------------------------------------------------------
    db, user, password, host, port = f.get_db_credentials("team4-redshift-secrets")
    connection1 = psycopg2.connect(f"dbname={db} user={user} password={password} host={host} port={port}")
    cur = connection1.cursor()
    print(connection1)
    # event ------------------------------------------------------------------------------------------------------------------------------------------
    print(event)
    message = json.loads(event["Records"][0]["body"])
    bucket = message["Records"][0]["s3"]['bucket']['name']
    s3_key = message["Records"][0]["s3"]['object']['key']
    print(bucket)
    print(s3_key)
    f.sqs_delete_from_queue(receipt=event["Records"][0]["receiptHandle"])
    #---------------------------------------------------------------------------------------------------------------------------------------------------
    if "transaction" in s3_key:
        copy_query = f"""COPY team4.transaction FROM 's3://{bucket}/{s3_key}' iam_role 'arn:aws:iam::370445109106:role/service-role/AmazonRedshift-CommandsAccessRole-20220705T230116' EXPLICIT_IDS DELIMITER ',' IGNOREHEADER as 1;"""
        cur.execute(copy_query)
        print("Transaction table has been loaded.")
    else:
        copy_query1 = f"""COPY team4.basket FROM 's3://{bucket}/{s3_key}' iam_role 'arn:aws:iam::370445109106:role/service-role/AmazonRedshift-CommandsAccessRole-20220705T230116' DELIMITER ',' EXPLICIT_IDS IGNOREHEADER as 1;"""
        cur.execute(copy_query1)
        print("Basket table has been loaded.")
    connection1.commit() 
    cur.close()
    connection1.close()