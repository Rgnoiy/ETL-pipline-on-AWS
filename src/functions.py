import re
import hashlib
import boto3
import pandas as pd
from io import StringIO


def get_db_credentials(credential_name):
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=credential_name)
    creds_string = response["Parameter"]["Value"]
    db, user, password, host, port = creds_string.split(",")
    
    return db, user, password, host, port


# def sqs_delete_from_queue(receipt):
#    sqs = boto3.client('sqs')
#    sqs.delete_message(
#    QueueUrl='https://sqs.eu-west-1.amazonaws.com/370445109106/team4-queue1',
#    ReceiptHandle=receipt
#    )
#    print('Deleted message from SQS queue.')

        
def hash(s: str) -> str:
    return str(int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16))[:10]
        
        
def SaveCSVToS3Bucket(df, s3_file_name, index=True, date=None):
    
    """Write dataframe to .csv and save it in another s3 bucket."""
    
    csv_buffer = StringIO()
    s3_resource = boto3.resource('s3')
    bucket = 'team4-transformed-data'
    # store .csv file in buffer
    df.to_csv(csv_buffer, index=index, date_format=date)
    # put .csv file into S3 bucket
    if date is None:
        s3_resource.Object(bucket, f'{s3_file_name}_basket.csv').put(Body=csv_buffer.getvalue())
        print(f"{s3_file_name}_basket.csv has been added to s3 bucket.")
    else:
        s3_resource.Object(bucket, f'{s3_file_name}_transaction.csv').put(Body=csv_buffer.getvalue())
        print(f"{s3_file_name}_transaction.csv has been added to s3 bucket.")
    
    

def ReadCSVandCleanDF(response):
    
    """Read .csv file from s3 bucket, generate hash id, drop columns."""
    
    df = pd.read_csv(response['Body'], names=['timestamp', 'store', 'customer_name', 'basket_items', 'total_price', 'cash_or_card', 'card_number'], parse_dates=['timestamp'], infer_datetime_format=True, dayfirst=True, cache_dates=True)
    df["order_id_pre_hash"] = str(df["timestamp"]) + df["store"] + df["customer_name"]
    df.index = df["order_id_pre_hash"].apply(lambda x: hash(x))
    df.drop(columns=['card_number'], inplace=True)
    df.drop(columns=['customer_name'], inplace=True)
    df.drop(columns=["order_id_pre_hash"], inplace=True)
    df.index.name = 'transaction_hash_id'
    
    return df
    
    
def ExplodedItems(df):
    
    """Generate a df where ordered items are in seperate rows."""
    
    # generate a new column with each row of column 'basket_items' in a format of list
    df["items"] = df["basket_items"].apply(lambda x: x.split(","))
    # spread products into different rows, replicating index.
    df = df.explode("items")
    # extract column 'items'
    items = df['items']
    # seperate price into an independent column
    result = items.str.rsplit(pat='-', n=1, expand=True)
    # remove leading and trailing space of the string
    result[0] = result[0].apply(lambda x: x.strip(' '))
    
    return result
        
        
def LoadProduct(df, cur, connection1):
    # drop duplicated product type
    product_list = df.drop_duplicates(subset=[0], keep='first', ignore_index=True)
    # rename column name
    product_list.rename(columns={0: 'product_name', 1: 'price'}, inplace=True)
    # convert product df into dict and iterate over it in order to extract each product name and insert it into db
    try:
        for product in product_list.to_dict('records'):
            sql = f"INSERT INTO product (product_name, price) SELECT '{product['product_name']}', {product['price']} WHERE NOT EXISTS (SELECT * FROM product WHERE product_name = '{product['product_name']}');"
            cur.execute(sql)
        connection1.commit()
        print("Product table has been loaded.")
    except:
        connection1.rollback()
        print("Product: transaction has been rolled back.")

def LoadStore(df, cur, connection1):

    # extract 'store' column + remove leading and trailing space of the string + convert it to df
    store = df['store'].apply(lambda x: x.strip(' ')).drop_duplicates().to_frame()
    # rename column names
    store.rename(columns={'store':'store_name'}, inplace=True)
    # gain store name
    store_name = store['store_name'][0]
    try:
        sql = f"INSERT INTO store (store_name) SELECT '{store_name}' WHERE NOT EXISTS (SELECT * FROM store WHERE store_name = '{store_name}');"
        cur.execute(sql)
        connection1.commit()
        print("Store table has been loaded.")
    except:
        connection1.rollback()
        print("Store: transaction has been rolled back.")
    return store_name
    
    
def BasketItemsDF(df, connection1):
    
    """Transform df to fit in basket table, return df."""
    
    # generate quantity column
    basket_items = df.groupby(df.index)[0].apply(lambda x: x.value_counts()).to_frame()
    basket_items = basket_items.reset_index()
    sql = '''SELECT * FROM product'''
    product_from_db = pd.read_sql(sql, connection1, index_col='product_id')
    # replace product name by its id
    basket_items['level_1'] = basket_items['level_1'].apply(lambda x: product_from_db[product_from_db.product_name == x].index[0])
    # rename columns
    basket_items.rename(columns={'level_1':'product_id', 0:'quantity'}, inplace=True)
    
    return basket_items
    
    
def TransactionDF(df, store_name, connection1):
    
    """Transform df to fit in transaction table, return df."""
    
    # drop unwanted columns
    transaction = df.drop(columns=['basket_items', 'items'])
    # replace store name by its id
    sql = f"""SELECT * FROM store WHERE store_name='{store_name}'"""
    store_from_db = pd.read_sql(sql, connection1, index_col='store_id')
    transaction['store'] = int(store_from_db.index[0])
    # Rename column names to match DB columns
    transaction.rename(columns={'store':'store_id', 'cash_or_card':'payment_method'}, inplace=True)
    
    return transaction