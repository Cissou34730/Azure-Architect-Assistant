"""
Helper Script: Auto-approve all documents in validation manifest
Use this for quick testing or when you trust the cleaning pipeline.
"""

import json
import sys

def auto_approve_all(manifest_file="validation_manifest.json"):
    """Set all documents to APPROVED status."""
    
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: {manifest_file} not found!")
        print("   Run Phase 1 first: python run_waf_phase1.py")
        return
    
    # Count current statuses
    before_counts = {}
    for doc in manifest:
        status = doc['status']
        before_counts[status] = before_counts.get(status, 0) + 1
    
    # Auto-approve all
    for doc in manifest:
        doc['status'] = 'APPROVED'
    
    # Save updated manifest
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("="*70)
    print("AUTO-APPROVAL COMPLETE")
    print("="*70)
    print(f"\nBefore:")
    for status, count in before_counts.items():
        print(f"  {status}: {count}")
    print(f"\nAfter:")
    print(f"  APPROVED: {len(manifest)}")
    print(f"\n✅ All {len(manifest)} documents approved!")
    print(f"📝 Updated: {manifest_file}")
    print(f"\n🚀 Ready for Phase 2: python run_waf_phase2.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Auto-approve all documents in validation manifest")
        print("\nUsage:")
        print("  python auto_approve_docs.py [manifest_file]")
        print("\nDefault manifest: validation_manifest.json")
    else:
        manifest = sys.argv[1] if len(sys.argv) > 1 else "validation_manifest.json"
        auto_approve_all(manifest)
