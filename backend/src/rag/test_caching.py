"""
Test index caching performance
"""
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Set environment variable
os.environ['WAF_STORAGE_DIR'] = r'C:\Users\cyril.beurier\OneDrive - Avanade\Documents 1\Azure-Architect-Assistant\data\knowledge_bases\waf\index'

# Import after setting env var
from query import WAFQueryService

print("Creating service instance 1...")
start1 = time.time()
service1 = WAFQueryService()
result1 = service1.query("What are the five pillars?", top_k=3)
time1 = time.time() - start1
print(f"Query 1 completed in {time1:.2f}s")
print(f"Answer length: {len(result1['answer'])} chars\n")

print("="*80)
print("Creating service instance 2 (should use cached index)...")
start2 = time.time()
service2 = WAFQueryService()
result2 = service2.query("What is cost optimization?", top_k=3)
time2 = time.time() - start2
print(f"Query 2 completed in {time2:.2f}s")
print(f"Answer length: {len(result2['answer'])} chars\n")

print("="*80)
print("SUMMARY:")
print(f"  First query:  {time1:.2f}s (includes 27s index load)")
print(f"  Second query: {time2:.2f}s (cached - should be ~8s)")
print(f"  Speedup: {time1/time2:.1f}x faster!")
