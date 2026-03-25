# inference.py
import argparse
from aide_backend import AIDEDetectorBackend
import os

def main():
    parser = argparse.ArgumentParser(description="AIDE Detector Inference CLI")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to your fine-tuned AIDE checkpoint (.pth)")
    parser.add_argument("--image", type=str, required=True, help="Path to the image you want to test")
    parser.add_argument("--device", type=str, default=None, help="Device to use (e.g., mps, cpu, cuda)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.checkpoint):
        print(f"Error: Checkpoint not found at {args.checkpoint}")
        return
    
    if not os.path.exists(args.image):
        print(f"Error: Image not found at {args.image}")
        return

    print(f"Initializing AIDE Backend with checkpoint: {args.checkpoint}...")
    detector = AIDEDetectorBackend(checkpoint_path=args.checkpoint, device=args.device)
    
    print(f"Running inference on: {args.image}...")
    prob = detector.predict_authenticity(args.image)
    
    if prob >= 0:
        result = "AI GENERATED" if prob > 0.5 else "REAL / HUMAN"
        print("-" * 30)
        print(f"Result: {result}")
        print(f"Probability of being AI Generated: {prob:.4f}")
        print("-" * 30)
    else:
        print("Inference failed. Check logs for details.")

if __name__ == "__main__":
    main()
