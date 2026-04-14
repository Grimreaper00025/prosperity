import pandas as pd
import glob

def analyze_drift():
    for f in sorted(glob.glob('prices_round_1_day_*.csv')):
        df = pd.read_csv(f, sep=';')
        
        df_pepper = df[df['product'] == 'INTARIAN_PEPPER_ROOT']
        df_osmium = df[df['product'] == 'ASH_COATED_OSMIUM']
        
        print(f"\nFile: {f}")
        
        if not df_pepper.empty:
            p_start = df_pepper['mid_price'].iloc[0]
            p_end = df_pepper['mid_price'].iloc[-1]
            print(f"Pepper: Start {p_start}, End {p_end}, Drift: {p_end - p_start}")
            
        if not df_osmium.empty:
            o_start = df_osmium['mid_price'].iloc[0]
            o_end = df_osmium['mid_price'].iloc[-1]
            print(f"Osmium: Start {o_start}, End {o_end}, Drift: {o_end - o_start}")

if __name__ == '__main__':
    analyze_drift()
