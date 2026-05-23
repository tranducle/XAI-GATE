# Explanation-Surface Governance in XAI-Enabled Network Intrusion Detection under Resource Constraints

This repository contains the official, reproducible open-source implementation of **XAI-Gate** and the **XAI-SurfaceBench** evaluation framework.

XAI-Gate is a detector-agnostic online service-governance framework that dynamically manages the explanation surface in Explainable AI (XAI)-enabled network intrusion detection systems. It balances packet forwarding QoS, explanation quality, explanation debt, and information exposure under severe resource limitations and adversarial explanation-demand inflation.

---

## 🌟 Key Features

*   **Detector-Agnostic Governance Layer:** Sits between any NIDS detector and the analyst-facing explanation interface, requiring zero re-training of classification or post-hoc explanation models.
*   **Dynamic Action Space:** Controls the explanation surface by dynamically selecting among 7 managed actions: *Suppress, Coarse, Delay, Full Local, Offload, Audit-only,* or *Redact*.
*   **Stochastic State-Aware Policies:** Jointly reasons about packet queue pressure, explanation backlog debt, offload RTT belief, suspicion of explanation-demand inflation, and remaining cumulative exposure budgets.
*   **XAI-SurfaceBench Stress-Test Suite:** Benchmarks and stress-tests policies across 9 distinct traffic and uncertainty regimes using calibrated real-world score streams.

---

## 📂 Project Structure

```
.
├── README.md                           # Main documentation
├── .gitignore                          # Git exclude rules
├── requirements.txt                    # Python dependencies
├── xai_gate_simulator.py               # Prototype reference simulator
├── calibration_training_pipeline.py    # Optional calibration model utility
├── xai_surfacebench/                   # Main reproducible benchmark package
│   ├── README.md                       # SurfaceBench documentation
│   ├── configs/                        # Reproducible JSON experiment definitions
│   ├── data/                           # Calibrated score-stream calibration anchors
│   ├── scripts/                        # Sanity, benchmark execution, and figure generation scripts
│   ├── results/                        # Raw and aggregated benchmark results
│   ├── tables/                         # Generated LaTeX tables for manuscript integration
│   └── figures/                        # Generated PDF diagnostics and subplots
```

---

## 🚀 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/tranducle/XAI-GATE.git
    cd XAI-GATE
    ```

2.  **Set Up a Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

## 📊 Reproducing Manuscript Results

To reproduce all numerical results, ablation studies, and diagnostic figures presented in the paper, execute the following command sequence from the `xai_surfacebench` directory:

```bash
cd xai_surfacebench

# 1. Run sanity verification to validate metrics and invariants
python3 scripts/sanity_check.py

# 2. Run the main 9-policy multi-regime benchmark suite
python3 scripts/run_benchmark.py --config configs/main.json

# 3. Run the adversarial demand-inflation sweeps
python3 scripts/run_benchmark.py --config configs/demand_sweep.json

# 4. Run the multi-objective Pareto frontier sweeps
python3 scripts/run_benchmark.py --config configs/frontier.json

# 5. Run the core mechanism ablation studies
python3 scripts/run_benchmark.py --config configs/ablations.json

# 6. Run the comprehensive robustness sweeps
python3 scripts/run_benchmark.py --config configs/robustness.json

# 7. Generate and polish all typeset figures and plots
python3 scripts/make_figures.py
```

Generated plots will be saved in `xai_surfacebench/figures/` (including the multi-objective frontiers and ablation diagnostics), and LaTeX typeset tables will be populated under `xai_surfacebench/tables/` ready for publication.

---

## 📈 Dataset Calibration & Provenance

The score streams and confusion matrices used to calibrate the simulator are derived from the following public datasets:

1.  **UNSW-NB15 Dataset:**
    *   *Source:* [UNSW Canberra Cyber Projects](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
    *   *Usage:* Anchors our modern NIDS score distributions. Includes a de-duplicated calibration stream that eliminates redundant feature rows to prevent train-test overlapping bias.
2.  **TON_IoT Dataset:**
    *   *Source:* [TON_IoT Telemetry Datasets](https://research.unsw.edu.au/projects/toniot-datasets)
    *   *Usage:* Calibrates score distributions under IoT-telemetry and edge forwarding limits.
3.  **KDD Cup 99 Dataset:**
    *   *Source:* [UCI KDD Archive](http://kdd.ics.uci.edu/databases/kddcup99/kddcup99.html)
    *   *Usage:* Provides a baseline legacy no-training score proxy.

For custom score streams, format CSV logs with `score` (or `calibrated_score`) and `label` (or `true_label`) columns, and configure the path mapping inside `xai_surfacebench/configs/`.

---

## ⚖️ License

This project is licensed under the MIT License - see the LICENSE file for details.
