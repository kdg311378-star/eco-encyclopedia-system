import sys
import os

# Set local mock env
os.environ["LOCAL_MOCK"] = "true"

from handlers.crawling_handler import lambda_handler as crawl_handler
from handlers.extract_handler import lambda_handler as extract_handler
from handlers.preprocess_handler import lambda_handler as preprocess_handler
from handlers.load_handler import lambda_handler as load_handler

def run_local(sci_name, common_name="국명 미상"):
    print(f"--- Local Pipeline Test: {sci_name} ---")
    event = {
        "scientific_name": sci_name,
        "common_name_ko": common_name,
        "batch_id": f"local_test_{sci_name.replace(' ', '_')}"
    }
    
    print("\n[Step 1] Crawl")
    event = crawl_handler(event, None)
    
    print("\n[Step 2] Extract")
    event = extract_handler(event, None)
    
    print("\n[Step 3] Preprocess")
    event = preprocess_handler(event, None)
    
    print("\n[Step 4] Load")
    res = load_handler(event, None)
    
    print(f"\nPipeline finished! Result: {res}")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sci = sys.argv[1]
        kor = sys.argv[2] if len(sys.argv) > 2 else "국명 미상"
        run_local(sci, kor)
    else:
        print("Usage: python run_pipeline.py <Scientific Name> [Korean Name]")
