#!/usr/bin/env python3
import os, json, time, subprocess, psutil, numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime
from pathlib import Path

BASELINE_FILE = Path.home() / "Documents/EmpireBot/monitoring/baseline.npy"
THRESHOLD     = 0.25
WINDOW        = 30

from healthcheck import alert_chain

def current_metrics() -> np.ndarray:
    cpu  = psutil.cpu_percent()
    mem  = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    try:
        latency = float(
            subprocess.check_output(["ping", "-c", "1", "-t", "2", "8.8.8.8"])
            .decode()
            .split("time=")[1]
            .split(" ms")[0]
        )
    except Exception:
        latency = 999.0
    return np.array([cpu, mem, disk, latency], dtype=float)

def load_model():
    if BASELINE_FILE.exists():
        baseline, sk_bytes = np.load(BASELINE_FILE, allow_pickle=True)
        model = IsolationForest()
        model.__setstate__(json.loads(sk_bytes))
        return baseline, model
    data = np.stack([current_metrics() for _ in range(10)])
    model = IsolationForest(contamination=0.05).fit(data)
    baseline = data.mean(axis=0)
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    np.save(BASELINE_FILE, [baseline, json.dumps(model.__getstate__())])
    return baseline, model

def main(loop=True):
    baseline, model = load_model()
    labels = ["CPU", "MEM", "DISK", "LAT"]

    while True:
        metrics = current_metrics()
        score   = 1 - (model.decision_function([metrics])[0] + 0.5)
        if score > THRESHOLD:
            worst = labels[int(np.argmax(np.abs(metrics - baseline)))]
            msg   = (f"🚨 Anomaly • {worst}\n"
                     f"Score: {score:.2f}\n"
                     f"Now: {dict(zip(labels, metrics))}")
            alert_chain(msg)
        if not loop:
            break
        time.sleep(WINDOW)

if __name__ == "__main__":
    main(loop=bool(int(os.getenv("LOOP", "1"))))

