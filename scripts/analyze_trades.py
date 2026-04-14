import pandas as pd

def analyze_trades():
    df = pd.read_csv('trades_round_1_day_0.csv', sep=';')
    for product in ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']:
        prod_df = df[df['symbol'] == product]
        print(f"--- {product} ---")
        print(f"Max Trade Price: {prod_df['price'].max()}")
        print(f"Min Trade Price: {prod_df['price'].min()}")
        print(f"Mean Trade Price: {prod_df['price'].mean()}")
        print(f"Std Dev: {prod_df['price'].std()}")

if __name__ == '__main__':
    analyze_trades()
