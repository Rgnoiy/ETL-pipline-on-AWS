import boto3
import json
import psycopg2
import src.functions as f
import src.database as dbc


def lambda_handler(event, context):
    #db connection and table creation-----------------------------------------------------------------------
    db, user, password, host, port = f.get_db_credentials("team4-redshift-secrets")
    connection1 = psycopg2.connect(f"dbname={db} user={user} password={password} host={host} port={port}")
    cur = connection1.cursor()
    dbc.create_tables(cur, connection1)
    #------------------------------------------------------------------------------------------------------
    s3 = boto3.client('s3')
    message = json.loads(event["Records"][0]["body"])
    s3_bucket = message["Records"][0]["s3"]['bucket']['name']
    print(s3_bucket)
    s3_key = message["Records"][0]["s3"]['object']['key']
    print(s3_key)
    s3_file_name = s3_key.rstrip('.csv')
    print(s3_file_name)
    response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
#    f.sqs_delete_from_queue(receipt=event["Records"][0]["receiptHandle"])
     # read csv---------------------------------------------------------------------------------------------------------------------------------
    df = f.ReadCSVandCleanDF(response)
    # Insert store name into db and return store name-------------------------------------------------------------------------------------------
    store_name = f.LoadStore(df, cur, connection1)
    # Load product name into db and drop duplicates---------------------------------------------------------------------------------------------
    f.LoadProduct(f.ExplodedItems(df), cur, connection1)
    # save transaction.csv to another bucket----------------------------------------------------------------------------------------------------
    f.SaveCSVToS3Bucket(f.TransactionDF(df, store_name, connection1), s3_file_name, date='%Y-%0m-%0d %H:%M:%S')
    # save basket.csv to another bucket---------------------------------------------------------------------------------------------------------
    f.SaveCSVToS3Bucket(f.BasketItemsDF(f.ExplodedItems(df), connection1), s3_file_name, index=False)
    
    cur.close()
    connection1.close()