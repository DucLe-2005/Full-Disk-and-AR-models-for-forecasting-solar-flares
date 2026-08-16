# Offline Evaluation

This package contains manually invoked dataset preparation, evaluation, and
reporting code. Offline modules reuse the production download stage and shared
model architecture; the production pipeline does not import this package.
Install its optional FITS/JSOC dependencies with
`pip install -r requirements/evaluation.txt`.

```text
evaluation/
|-- reference/                    versioned flare catalogs/reference data
|-- dataset.py                    MagnetogramDataset
|-- preprocessing.py             grayscale 512x512 transform
|-- model_loader.py               fold-1 full-disk model loader
|-- inference.py                  fold-1 batched softmax inference
|-- labels.py                     24-hour M/X flare labels and dataset.csv
|-- metrics.py                    confusion matrix and skill metrics
|-- download_2025_magnetograms.py one-off 2025 Helioviewer archive job
|-- fits_preprocessing.py         optional manual FITS conversion utilities
|-- jsoc_download.py              optional manual JSOC FITS download
|-- localization.py               event-position projection and hull coverage metrics
|-- evaluate_active_region_localization.py
|                                 attribution-proposal localization evaluation
`-- evaluate_2025.py              end-to-end evaluation entrypoint
```

Download the 2025 archive:

```powershell
venv\Scripts\python.exe -m prediction.evaluation.download_2025_magnetograms
```

Create labels, run inference with `batch_size=32`, and calculate metrics:

```powershell
venv\Scripts\python.exe -m prediction.evaluation.evaluate_2025
```

Evaluate whether attribution proposals cover the active regions associated
with flare events in `data/events.csv`:

```powershell
venv\Scripts\python.exe -m prediction.evaluation.evaluate_active_region_localization
```

For each magnetogram with an M- or X-class event in its next 24-hour window,
this generates proposed regions, extracts 512px crops, runs the ResNet
active-region classifier, and evaluates each proposal with the same confusion
matrix, accuracy, precision, recall, F1, and TSS metrics as full-disk
evaluation. A proposal is positive when it contains an actual M/X active
region in 512px coordinates. Results are written under
`data/active_region_evaluation_2025/`; intermediate attribution maps and crop
files are not saved.

Generated files are written under `data/` and are intentionally not versioned.
`data/events.csv` is the source for M/X flare labels and localization events.
