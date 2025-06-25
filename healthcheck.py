# healthcheck.py
import os

def alert_chain(msg="⚠️ Autoscaler Alert"):
    print(msg)
    os.system(f'echo "{msg}" | tee -a logs/autoscaler.log')

