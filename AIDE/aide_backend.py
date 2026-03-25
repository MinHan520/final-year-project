# aide_backend.py
import torch
from torchvision import transforms
from PIL import Image
import os
import logging

# Mirroring the repository's modular import structure
from models.AIDE import AIDE 
from data.dct import DCT_base_Rec_Module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIDEDetectorBackend:
    """
    A persistent backend class designed to keep the AIDE mixture-of-experts model 
    in VRAM for low-latency, real-time inference requests.
    """
    def __init__(self, checkpoint_path: str, device: str = None):
        # Dynamically assign hardware acceleration
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing AIDE Backend on device: {self.device}")
        
        # Instantiate the model architecture utilizing local pre-trained backbones
        self.model = AIDE(
            resnet_path='pretrained_ckpts/resnet50.pth',
            convnext_path='pretrained_ckpts/open_clip_pytorch_model.bin'
        )
        
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Critical Error: AIDE checkpoint missing at {checkpoint_path}")

        logger.info(f"Loading pre-trained weights from {checkpoint_path}...")
        # Load the fine-tuned serialization dictionary
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        
        # Handle potential dictionary wrapping from Distributed Data Parallel (DDP)
        if 'model' in state_dict:
            self.model.load_state_dict(state_dict['model'])
        elif 'state_dict' in state_dict:
            self.model.load_state_dict(state_dict['state_dict'])
        else:
            self.model.load_state_dict(state_dict)
        
        # Mount the network to VRAM and explicitly enforce evaluation mode
        # This disables stochastic dropout and locks BatchNorm running statistics
        self.model.to(self.device)
        self.model.eval() 

        # Initialize the DCT extraction module
        self.dct_module = DCT_base_Rec_Module()

        # Transformation pipelines from data.datasets
        self.transform_before = transforms.Compose([
            transforms.ToTensor(),
        ])
        
        self.transform_final = transforms.Compose([
            transforms.Resize((256, 256), interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict_authenticity(self, image_path: str) -> float:
        """
        Executes a deterministic forward pass on a single image tensor.
        Returns the localized probability of image being AI-generated (0.0 to 1.0).
        """
        try:
            # Load and convert to RGB
            image = Image.open(image_path).convert('RGB')
            
            # 1. Initial transform (ToTensor)
            tensor_init = self.transform_before(image).to(self.device)
            
            # 2. Extract DCT features (Hybrid Expert streams)
            with torch.no_grad():
                x_minmin, x_maxmax, x_minmin1, x_maxmax1 = self.dct_module(tensor_init)
            
                # 3. Apply final resizing and normalization to each stream
                x_0 = self.transform_final(tensor_init)
                x_minmin = self.transform_final(x_minmin)
                x_maxmax = self.transform_final(x_maxmax)
                x_minmin1 = self.transform_final(x_minmin1)
                x_maxmax1 = self.transform_final(x_maxmax1)
                
                # 4. Stack into the 5-stream tensor [1, 5, 3, 256, 256]
                input_tensor = torch.stack([x_minmin, x_maxmax, x_minmin1, x_maxmax1, x_0], dim=0).unsqueeze(0)
            
                # Execute the hybrid forward pass
                logits = self.model(input_tensor)
                
                # Apply Softmax (the model has 2 output classes)
                # Looking at main_finetune.py, it uses CrossEntropyLoss with 2 classes
                # index 1 is usually the "fake" class in these benchmarks
                probs = torch.softmax(logits, dim=1)
                probability = probs[0, 1].item()
                
            return probability
            
        except Exception as e:
            logger.error(f"Inference failed on {image_path}: {str(e)}")
            return -1.0

# === Agent Testing Block ===
if __name__ == "__main__":
    # Example execution for the agent to verify the class compiles
    # Note: This will fail at runtime until the .pth files are actually downloaded into pretrained_ckpts/
    print("AIDEDetectorBackend class successfully compiled.")
