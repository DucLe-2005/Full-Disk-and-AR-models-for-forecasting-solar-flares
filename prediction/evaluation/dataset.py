from pathlib import Path

import pandas as pd
from PIL import Image
from torch.utils.data import Dataset


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_COLUMNS = {"timestamp", "image_path", "true_label"}


class MagnetogramDataset(Dataset):
    """Load labeled full-disk magnetograms listed in a dataset CSV."""

    def __init__(self, dataset_path: str | Path, transform) -> None:
        self.records = pd.read_csv(dataset_path)
        missing_columns = REQUIRED_COLUMNS.difference(self.records.columns)
        if missing_columns:
            raise ValueError(
                f"Dataset is missing required columns: {sorted(missing_columns)}"
            )
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict:
        record = self.records.iloc[index]
        image_path = Path(record["image_path"])
        if not image_path.is_absolute():
            image_path = REPOSITORY_ROOT / image_path

        with Image.open(image_path) as image:
            image_tensor = self.transform(image.convert("L"))

        return {
            "image": image_tensor,
            "timestamp": record["timestamp"],
            "image_path": record["image_path"],
            "true_label": int(record["true_label"]),
        }
