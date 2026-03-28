# Solar Flare Forecasting Pipeline

This project runs a two-stage solar flare workflow on HMI magnetogram data.

1. Download the latest full-disk HMI FITS image from JSOC.
2. Convert the FITS file to a grayscale JPG.
3. Run the 4-fold full-disk classifier.
4. Build explanation maps and propose active-region bounding boxes.
5. Crop those regions from the original 4096x4096 FITS image.
6. Resize each crop to 512x512 and run AR patch models on them.

The main entrypoint is [`pipeline.py`](/C:/Users/Duc/Desktop/Full-Disk-and-AR-models-for-forecasting-solar-flares/pipeline.py).

## Requirements

- Python 3.10+
- A JSOC-registered email address
- Model weights present in the repo under:
  - `modeling/full_disk/trained_models/`
  - `modeling/ar_patch/trained_models/`

## Setup

Create a `.env` file in the repo root:

```env
JSOC_EMAIL=your_email@example.com
```

Optional: create and activate a virtual environment, then install the required packages.

## Run The Pipeline

Run the default pipeline:

```powershell
python pipeline.py
```

Run with explanation plots enabled:

```powershell
python pipeline.py --show-plots
```

Run with multiple AR models:

```powershell
python pipeline.py --ar-models resnet mobilenet mobilevit
```

Run with custom thresholds:

```powershell
python pipeline.py --threshold 0.5 --ar-threshold 0.5 --percentile-thresh 95
```

## Common Options

```powershell
python pipeline.py `
  --fits-out-dir data/hmi_fits `
  --jpg-out-dir data/hmi_jpg `
  --region-crop-out-dir data/ar_crops `
  --heatmap-fold-strategy predicted `
  --top-k 5 `
  --pad-ratio 0.15
```

Important flags:

- `--show-plots`: display Grad-CAM, Integrated Gradients, and DeepLiftShap maps.
- `--ar-models`: choose one or more of `resnet`, `mobilenet`, `mobilevit`.
- `--heatmap-fold-strategy`: `predicted` or `first`.
- `--target`: explain class `0` or `1`; default explains the predicted class.

## Outputs

The pipeline prints:

- downloaded FITS path
- generated JPG path
- 4-fold full-disk prediction
- selected heatmap fold and weight file
- proposed active-region boxes
- AR model predictions for each cropped region

Generated files are written to:

- `data/hmi_fits/`
- `data/hmi_jpg/`
- `data/ar_crops/`

## Notes

- JSOC access will fail if the email is not registered with JSOC exports.
- The full-disk stage chooses one fold for heatmap generation after averaging all four fold predictions.
- AR predictions are run on resized region crops, not on the full-disk image.
