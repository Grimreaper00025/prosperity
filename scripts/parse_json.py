import json
import sys
import pandas as pd

def parse_json(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        print("Keys in json:", data.keys())
        print("Profit:", data.get('profit'))
        
        # Check activitiesLog
        activities = data.get('activitiesLog', [])
        if activities:
            print(f"Number of activities: {len(activities)}")
            # first 5 activities
            for i, row in enumerate(activities[:5]):
                print(row)

        
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    parse_json('103427.json')
