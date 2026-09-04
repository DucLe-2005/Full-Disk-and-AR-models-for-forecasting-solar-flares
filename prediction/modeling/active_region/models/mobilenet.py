import torch
# All neural network modules, nn.Linear, nn.Conv2d, BatchNorm, Loss functions
import torch.nn as nn
import torchvision.models as models

class MobileNet(nn.Module):
    def __init__(self) -> None:
        super(MobileNet, self).__init__()

        #add one convolution layer at the beginning
        self.first_conv_layer = nn.Sequential(
            nn.Conv2d(1, 3, kernel_size=3, stride=2, padding=1, bias=True),
            nn.ReLU(inplace=True)
            )
        
        # Load mobilenet v3
        torch.hub._validate_not_a_forked_repo=lambda a,b,c: True
        self.model = torch.hub.load('pytorch/vision:v0.10.0', 'mobilenet_v3_large', pretrained=True)
        self.model.classifier[-1] = nn.Linear(1280, 2)


    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.first_conv_layer(x)
        x = self.model(x)
        return x