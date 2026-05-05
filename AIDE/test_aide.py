import shutil
import os
from aide_backend import AIDEDetectorBackend

def test_inference():
    # 1. Setup paths
    checkpoint = 'results/progan_train.pth'
    sample_image = 'dataset/progan/Chameleon/test/1_fake/00005a79-1347-4bb6-bb01-4d80c2d856e7.jpg'
    
    if not os.path.exists(checkpoint):
        print(f"Error: checkpoint {checkpoint} not found.")
        return
    
    if not os.path.exists(sample_image):
        print(f"Error: sample_image {sample_image} not found.")
        return

    # 2. Initialize Backend (Bypassing MPS for debugging)
    try:
        backend = AIDEDetectorBackend(checkpoint_path=checkpoint, device="cpu")
        print("Backend initialized successfully.")
        
        # 3. Predict probability
        prob = backend.predict_authenticity(sample_image)
        print(f"Analysis complete for {sample_image}")
        print(f"Result: {prob:.4f} (Probability of being AI-generated)")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    test_inference()
