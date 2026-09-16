# Data Sources and Provenance

This repository does not distribute raw intrusion-detection datasets, participant data, private traces, credentials, or machine-specific artifacts. Dataset preparation scripts download or derive only the inputs required for local reproduction.

## KDD Cup 99

- Source: UCI / KDD Cup 1999 archive
- Public page: http://kdd.ics.uci.edu/databases/kddcup99/kddcup99.html
- Role: legacy no-training calibration anchor and sanity reference

The calibration utility uses the public dataset interface provided through scikit-learn where applicable.

## UNSW-NB15

- Source: UNSW Canberra Cyber project
- Public page: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- Dataset paper DOI: 10.1109/MilCIS.2015.7348942
- Role: modern NIDS score-stream calibration anchor

Two workflows are provided:

1. the public train/test calibration anchor;
2. a de-duplicated anchor that removes feature duplicates within each split and test rows whose feature hashes occur in the de-duplicated training split.

Raw files are downloaded locally and are ignored by Git.

## TON_IoT

- Source: UNSW Canberra Cyber project
- Public page: https://research.unsw.edu.au/projects/toniot-datasets
- Dataset paper DOI: 10.1109/ACCESS.2020.3022862
- Role: IoT/IIoT calibrated score-stream anchor

The public workflow de-duplicates the selected network-flow data before the held-out calibration split.

## CICIoT2023

- Official dataset page: https://www.unb.ca/cic/datasets/iotdataset-2023.html
- Dataset paper DOI: 10.3390/s23135941
- Reproducible parquet mirror used by the acquisition script: `Lystea/CICIOT2023-PARQUET` on Hugging Face
- Role: timestamp-preserving temporal replay and hardware-validation input preparation

The acquisition script selects a fixed set of calibration and replay captures declared directly in `scripts/download_ciciot2023_temporal.py`. File hashes, schema checks, label checks, and timestamp integrity metadata are generated locally.

## Data handling boundary

- Raw dataset files are not committed.
- Derived score streams, parquet files, trained calibration objects, and runtime CSV results are not committed.
- No human-subject or personally identifying data are part of this release.
- Dataset licenses and terms remain those of the original providers. Users are responsible for complying with the relevant source terms.
