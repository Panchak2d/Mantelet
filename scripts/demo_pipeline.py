import argparse
import sys
from pathlib import Path

# Add src to the Python path so this script can run easily
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mantelet import image

def main():
    parser = argparse.ArgumentParser(description="Run an image through the Mantelet platform pipeline.")
    parser.add_argument("input", help="Path to the input image")
    parser.add_argument("output", help="Path to save the output image (e.g., out.jpg)")
    parser.add_argument("--noise", action="store_true", help="Add experimental Gaussian noise")
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: Could not find '{args.input}'")
        sys.exit(1)
        
    print(f"Loading {args.input}...")
    img = image.load_image(args.input)
    print(f"Original size: {img.size}")
    
    print("Running platform pipeline (resize to 512, crop to 80%, JPEG compress)...")
    processed = image.platform_pipeline(img)
    print(f"Processed size: {processed.size}")
    
    if args.noise:
        print("Adding Gaussian noise...")
        processed = image.add_gaussian_noise(processed, std=15.0)
        
    print(f"Saving to {args.output}...")
    image.save_image(processed, args.output)
    print("Done!")

if __name__ == "__main__":
    main()
