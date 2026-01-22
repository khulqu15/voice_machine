import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# Load nominal response
# =========================
df = pd.read_csv("drone_data (2).csv")

np.random.seed(7)
N = len(df)
dt = 0.01
t = np.arange(N) * dt

# =========================
# Disturbance generation
# =========================

# Wind gust (colored noise)
wind = 0.4 * np.convolve(np.random.randn(N), np.ones(20)/20, mode='same')

# Payload change (1.5 kg step + dynamics)
payload = np.zeros(N)
payload[int(0.3*N):] = 1.5
payload_dyn = payload * (1 - np.exp(-t))

# Sensor / actuator noise
noise = 0.05 * np.random.randn(N)

# Combined disturbance
d = wind + 0.3 * payload_dyn + noise

dist_energy = np.trapz(d**2, dx=dt)
dist_peak = np.max(np.abs(d))

# =========================
# Metrics computation
# =========================

controllers = ["SMC", "SMC+PSO", "SMC+GA", "SMC+GNN"]

DEA, OSR, RCE, GRS = [], [], [], []

for ctrl in controllers:
    y = df[ctrl].values

    dea = np.trapz(y**2, dx=dt) / dist_energy
    osr = np.max(np.abs(y)) / dist_peak
    rce = np.sqrt(np.mean(y**2))

    DEA.append(dea)
    OSR.append(osr)
    RCE.append(rce)
    GRS.append(1.0 / (dea + osr + rce))

# =========================
# Plot robustness metrics
# =========================

metrics = {
    "DEA": DEA,
    "OSR": OSR,
    "RCE": RCE,
    "GRS": GRS
}

plt.figure(figsize=(10,6))

x = np.arange(len(controllers))
width = 0.2

for i, (name, values) in enumerate(metrics.items()):
    plt.bar(
        x + i*width,
        values,
        width=width,
        label=name
    )

plt.xticks(x + 1.5*width, controllers)
plt.ylabel("Metric Value")
plt.title("Time-Domain Disturbance Rejection Metrics under Wind, Payload, and Noise")
plt.grid(axis="y", alpha=0.4)
plt.legend()
plt.tight_layout()
plt.show()
