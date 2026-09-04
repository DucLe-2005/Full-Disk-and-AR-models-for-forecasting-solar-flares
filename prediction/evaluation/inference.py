import pandas as pd
import torch


def run_batch_inference(model, data_loader) -> pd.DataFrame:
    """Run the loaded fold-1 full-disk model over a DataLoader."""
    device = next(model.parameters()).device
    predictions = []

    i = 1
    with torch.no_grad():
        for batch in data_loader:
            print("Running inference for batch", i)
            i += 1
            images = batch["image"].to(device)
            logits = model(images)  # [batch_size, 2]: non-flare and flare logits
            probabilities = torch.softmax(logits, dim=1).cpu()

            for timestamp, image_path, true_label, probability in zip(
                batch["timestamp"],
                batch["image_path"],
                batch["true_label"].tolist(),
                probabilities.tolist(),
            ):
                predictions.append(
                    {
                        "timestamp": timestamp,
                        "image_path": image_path,
                        "true_label": true_label,
                        "p_non_flare": probability[0],
                        "p_flare": probability[1],
                    }
                )

    return pd.DataFrame(
        predictions,
        columns=["timestamp", "image_path", "true_label", "p_non_flare", "p_flare"],
    )
