"""
Test Script for Generic Ingestion API
Tests the new /api/ingestion endpoints
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def test_create_kb():
    """Test creating a new KB"""
    print("\n1. Testing KB Creation...")
    
    payload = {
        "kb_id": "test-azure-docs",
        "name": "Azure Documentation Test",
        "description": "Test KB for Azure documentation",
        "source_type": "web_documentation",
        "source_config": {
            "start_urls": ["https://learn.microsoft.com/en-us/azure/architecture/"],
            "allowed_domains": ["learn.microsoft.com"],
            "path_prefix": "/en-us/azure/architecture/",
            "follow_links": True,
            "max_pages": 10  # Small for testing
        },
        "embedding_model": "text-embedding-3-small",
        "chunk_size": 800,
        "chunk_overlap": 120,
        "profiles": ["chat", "kb-query"],
        "priority": 2
    }
    
    response = requests.post(f"{BASE_URL}/api/ingestion/kb/create", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_start_ingestion(kb_id: str):
    """Test starting ingestion"""
    print(f"\n2. Testing Ingestion Start for KB: {kb_id}...")
    
    payload = {"kb_id": kb_id}
    response = requests.post(f"{BASE_URL}/api/ingestion/kb/{kb_id}/start", json=payload)
    print(f"Status Code: {response.status_code}")
    
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        return data.get("job_id")
    return None


def test_get_status(kb_id: str):
    """Test getting job status"""
    print(f"\n3. Testing Status Check for KB: {kb_id}...")
    
    response = requests.get(f"{BASE_URL}/api/ingestion/kb/{kb_id}/status")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_list_jobs():
    """Test listing all jobs"""
    print("\n4. Testing Job List...")
    
    response = requests.get(f"{BASE_URL}/api/ingestion/jobs")
    print(f"Status Code: {response.status_code}")
    
    data = response.json()
    print(f"Found {len(data.get('jobs', []))} jobs")
    
    for job in data.get('jobs', [])[:3]:  # Show first 3
        print(f"  - {job['kb_id']}: {job['status']} ({job['phase']}) - {job['progress']:.1f}%")
    
    return response.status_code == 200


def test_cancel_job(kb_id: str):
    """Test cancelling a job"""
    print(f"\n5. Testing Job Cancellation for KB: {kb_id}...")
    
    response = requests.post(f"{BASE_URL}/api/ingestion/kb/{kb_id}/cancel")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False


def monitor_job(kb_id: str, max_checks: int = 5):
    """Monitor job progress"""
    print(f"\n6. Monitoring Job Progress (max {max_checks} checks)...")
    
    for i in range(max_checks):
        response = requests.get(f"{BASE_URL}/api/ingestion/kb/{kb_id}/status")
        if response.status_code != 200:
            print(f"Error getting status: {response.status_code}")
            break
        
        data = response.json()
        status = data['status']
        phase = data['phase']
        progress = data['progress']
        message = data['message']
        
        print(f"  [{i+1}/{max_checks}] {status} | {phase} | {progress:.1f}% | {message}")
        
        if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
            print(f"\n✓ Job finished with status: {status}")
            break
        
        time.sleep(2)


def main():
    """Run all tests"""
    print("=" * 60)
    print("Generic Ingestion API Test Suite")
    print("=" * 60)
    
    # Test 1: Create KB
    if not test_create_kb():
        print("\n✗ KB creation failed - stopping tests")
        return
    
    kb_id = "test-azure-docs"
    
    # Test 2: Start ingestion
    job_id = test_start_ingestion(kb_id)
    if not job_id:
        print("\n✗ Ingestion start failed - stopping tests")
        return
    
    print(f"\n✓ Job started: {job_id}")
    
    # Test 3: Get status
    time.sleep(1)
    test_get_status(kb_id)
    
    # Test 4: List jobs
    test_list_jobs()
    
    # Test 5: Monitor progress
    monitor_job(kb_id, max_checks=3)
    
    # Test 6: Cancel job (if still running)
    time.sleep(1)
    response = requests.get(f"{BASE_URL}/api/ingestion/kb/{kb_id}/status")
    if response.status_code == 200:
        status = response.json()['status']
        if status == 'RUNNING':
            test_cancel_job(kb_id)
    
    print("\n" + "=" * 60)
    print("Test suite completed")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to backend server")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Error: {e}")
