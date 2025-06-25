#!/usr/bin/env python3
import os
import time
import json
import psutil
from prometheus_client import start_http_server, Gauge
from sklearn.ensemble import IsolationForest

class EmpireMonitor:
    def __init__(self):
        self.metrics = {
            'cpu': Gauge('empire_cpu', 'CPU usage %'),
            'mem': Gauge('empire_mem', 'Memory usage %'),
            'anomaly_score': Gauge('empire_anomaly', 'Anomaly detection score')
        }
        self.model = IsolationForest(n_estimators=100)
        self.baseline = []
        self.alert_threshold = 0.8
        
    def collect_metrics(self):
        return {
            'cpu': psutil.cpu_percent(),
            'mem': psutil.virtual_memory().percent
        }

    def check_anomaly(self, metrics):
        if len(self.baseline) < 30:
            self.baseline.append(list(metrics.values()))
            return 0
        if len(self.baseline) == 30:
            self.model.fit(self.baseline)
        score = self.model.decision_function([list(metrics.values())])[0]
        return float(1 - (score + 0.5))

    def run(self):
        start_http_server(8000)
        while True:
            metrics = self.collect_metrics()
            anomaly_score = self.check_anomaly(metrics)
            for name, value in metrics.items():
                self.metrics[name].set(value)
            self.metrics['anomaly_score'].set(anomaly_score)

            # Log to file
            with open('monitor.log', 'a') as f:
                f.write(f"{time.time()},{metrics['cpu']},{metrics['mem']},{anomaly_score}\n")

            # Alert if needed
            if anomaly_score > self.alert_threshold:
                self.trigger_alert(metrics, anomaly_score)

            time.sleep(300)

    def trigger_alert(self, metrics, score):
        msg = f"🚨 Anomaly Detected (Score: {score:.2f})\nCPU: {metrics['cpu']}% | MEM: {metrics['mem']}%"
        os.system(f"python3 alert_chain.py '{msg}'")

if __name__ == "__main__":
    EmpireMonitor().run()
