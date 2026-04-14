import optuna
import json
import subprocess
import re
import os

def objective(trial):
    config = {
        'INTARIAN_PEPPER_ROOT': {
            'c0': trial.suggest_float('ip_c0', -5.0, 5.0),
            'c1': trial.suggest_float('ip_c1', -10.0, 10.0),
            'c2': trial.suggest_float('ip_c2', -10.0, 10.0),
            'c3': trial.suggest_float('ip_c3', -10.0, 10.0),
            'c4': trial.suggest_float('ip_c4', -1.0, 1.0),
            'pos_limit': 20
        },
        'ASH_COATED_OSMIUM': {
            'c0': trial.suggest_float('aco_c0', -5.0, 5.0),
            'c1': trial.suggest_float('aco_c1', -10.0, 10.0),
            'c2': trial.suggest_float('aco_c2', -10.0, 10.0),
            'c3': trial.suggest_float('aco_c3', -10.0, 10.0),
            'c4': trial.suggest_float('aco_c4', -1.0, 1.0),
            'pos_limit': 20
        }
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f)
        
    cmd = ['python3', '-m', 'prosperity4bt', 'scripts/template.py', '1', '--data', '.', '--no-out', '--no-progress']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # Parse PnL from output
        # Format usually looks like:
        # Risk metrics (full trading period):
        #   final_pnl: X
        match = re.search(r'final_pnl:\s*(-?\d+(\.\d+)?)', output)
        if match:
            return float(match.group(1))
        else:
            return 0.0
    except Exception as e:
        print(f"Error running backtest: {e}")
        return 0.0

if __name__ == '__main__':
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=30)
    
    print("Best params:", study.best_params)
    print("Best PnL:", study.best_value)
    
    # Save best config
    best_config = {
        'INTARIAN_PEPPER_ROOT': {
            'c0': study.best_params['ip_c0'],
            'c1': study.best_params['ip_c1'],
            'c2': study.best_params['ip_c2'],
            'c3': study.best_params['ip_c3'],
            'c4': study.best_params['ip_c4'],
            'pos_limit': 20
        },
        'ASH_COATED_OSMIUM': {
            'c0': study.best_params['aco_c0'],
            'c1': study.best_params['aco_c1'],
            'c2': study.best_params['aco_c2'],
            'c3': study.best_params['aco_c3'],
            'c4': study.best_params['aco_c4'],
            'pos_limit': 20
        }
    }
    with open('best_config.json', 'w') as f:
        json.dump(best_config, f, indent=4)
