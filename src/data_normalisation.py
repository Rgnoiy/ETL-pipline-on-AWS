import pandas as pd


df = pd.read_csv('example_transactions.csv')

df.drop(columns=['card_number'], inplace=True)
df.drop(columns=['customer_name'], inplace=True)

df["items"] = df["basket_items"].apply(lambda x: x.split(","))
df1 = df.explode("items")
items = df1['items']
store = df['store'].drop_duplicates().to_frame()                # TODO


transaction = df.drop(columns=['basket_items', 'items'])
transaction['store'] = transaction['store'].apply(lambda x: pd.Index(store['store']).get_loc(x)+1)  # TODO


# separate product&flavor and price
result = items.str.rsplit(pat='-', n=1, expand=True)
result[0] = result[0].apply(lambda x: x.strip(' '))


# product list with price
products = result.reset_index(drop=True)
products[0] = products[0].apply(lambda x: x.strip(' '))
product_list = products.drop_duplicates(subset=[0], keep='first', ignore_index=True)    # TODO


# transac id + product_name + quantity
basket_items = result[0].to_frame()
basket_items = basket_items.groupby(basket_items.index)[0].apply(lambda x: x.value_counts()).to_frame()
basket_items = basket_items.reset_index()


# transac id + product_id + quantity
basket_items['level_1'] = basket_items['level_1'].apply(lambda x: pd.Index(product_list[0]).get_loc(x)+1)
basket_items['level_0'] = basket_items['level_0'] + 1
basket_items_with_quantity = basket_items   # TODO





