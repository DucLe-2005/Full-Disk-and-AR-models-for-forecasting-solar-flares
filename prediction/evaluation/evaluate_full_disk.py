from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader

from prediction.evaluation.dataset import MagnetogramDataset
from prediction.evaluation.inference import run_batch_inference
from prediction.evaluation.labels import DATASET_PATH, REPOSITORY_ROOT, create_24h_labels
from prediction.evaluation.metrics import accuracy, confusion_matrix, f1, precision, recall, tss, hss
from prediction.modeling.full_disk.model import Custom_AlexNet


OUTPUT_DIRECTORY = REPOSITORY_ROOT / "data/evaluation_2025"
PREDICTIONS_PATH = OUTPUT_DIRECTORY / "full_disk_predictions.csv"
METRICS_PATH = OUTPUT_DIRECTORY / "metrics.csv"
WEIGHT_PATH = REPOSITORY_ROOT / "prediction/modeling/full_disk/trained_models/new-fold1.pth"


def load_full_disk_model() -> Custom_AlexNet:
    """Load the fold-1 full-disk checkpoint for offline evaluation."""
    if not WEIGHT_PATH.is_file():
        raise FileNotFoundError(f"Full-disk model weights not found: {WEIGHT_PATH}")

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(WEIGHT_PATH, map_location=device)
    model = Custom_AlexNet(train=False).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model


def main() -> None:
    dataset_records = create_24h_labels()
    transform = Compose([Resize((512, 512)), ToTensor(),])
    dataset = MagnetogramDataset(DATASET_PATH, transform=transform)
    data_loader = DataLoader(dataset, batch_size=24, shuffle=False, num_workers=2)

    model = load_full_disk_model()
    predictions = run_batch_inference(model, data_loader)
    predictions["predicted_label"] = (predictions["p_flare"] >= 0.5).astype(int)
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS_PATH, index=False)

    matrix = confusion_matrix(predictions["true_label"], predictions["predicted_label"])
    summary = {
        **matrix,
        "accuracy": accuracy(matrix),
        "precision": precision(matrix),
        "recall": recall(matrix),
        "f1": f1(matrix),
        "tss": tss(matrix),
        "hss": hss(matrix),
        
    }
    pd.DataFrame([summary]).to_csv(METRICS_PATH, index=False)

    print(f"Dataset records: {len(dataset_records)}")
    print(f"Predictions: {PREDICTIONS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(pd.Series(summary))


if __name__ == "__main__":
    main()
