import json
import io
import pandas as pd

def analyze_judge_data(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    activities_csv = data.get('activitiesLog', '')
    
    # Read the CSV string into pandas
    df = pd.read_csv(io.StringIO(activities_csv), sep=';')
    
    print("Columns:", df.columns.tolist())
    
    # Let's see the price trend for INTARIAN_PEPPER_ROOT
    df_pepper = df[df['product'] == 'INTARIAN_PEPPER_ROOT']
    df_osmium = df[df['product'] == 'ASH_COATED_OSMIUM']
    
    print("\n--- INTARIAN_PEPPER_ROOT ---")
    print(df_pepper[['timestamp', 'mid_price']].head())
    print(df_pepper[['timestamp', 'mid_price']].tail())
    print("Min mid_price:", df_pepper['mid_price'].min())
    print("Max mid_price:", df_pepper['mid_price'].max())
    
    print("\n--- ASH_COATED_OSMIUM ---")
    print(df_osmium[['timestamp', 'mid_price']].head())
    print(df_osmium[['timestamp', 'mid_price']].tail())
    print("Min mid_price:", df_osmium['mid_price'].min())
    print("Max mid_price:", df_osmium['mid_price'].max())
    
    # Let's check positions over time
    print("\nFinal Position and PnL")
    if 'profit_and_loss' in df_pepper.columns:
        print("Pepper PnL:", df_pepper['profit_and_loss'].iloc[-1])
    if 'profit_and_loss' in df_osmium.columns:
        print("Osmium PnL:", df_osmium['profit_and_loss'].iloc[-1])

if __name__ == '__main__':
    analyze_judge_data('103427.json')
