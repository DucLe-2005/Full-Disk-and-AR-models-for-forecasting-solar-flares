import torch
from PIL import Image
from torchvision.transforms import Compose, Resize, ToTensor

from prediction.modeling.full_disk.ensemble import (
    load_full_disk_model,
)

use_cuda = torch.cuda.is_available()
device = torch.device("cuda:0" if use_cuda else "cpu")

transformations = Compose([
    Resize((512, 512)),
    ToTensor()
])

def predict_full_disk(
    image_path,
    threshold=0.5,
    transform=transformations
):
    """
    Predict one image using the fold-1 full-disk model.

    Args:
        image_path (str): path to one JPG image
        threshold (float): threshold for positive prediction
        transform: torchvision transform

    Returns:
        dict containing non-flare and flare probabilities and predicted class
    """
    with Image.open(image_path) as image:
        image_tensor = transform(image.convert("L")).unsqueeze(0).to(device)

    model = load_full_disk_model(device=device)
    with torch.no_grad():
        probabilities = torch.softmax(model(image_tensor), dim=1)
        non_flare_prob = probabilities[0, 0].item()
        flare_prob = probabilities[0, 1].item()

    pred_class = int(flare_prob >= threshold)

    return {
        "image_path": image_path,
        "p_non_flare": non_flare_prob,
        "p_flare": flare_prob,
        "pred_class": pred_class
    }
