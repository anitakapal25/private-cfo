#!/usr/bin/env python3
"""Simple test script using only standard library"""
import urllib.request
import urllib.parse
import json
import base64

# Test health endpoint
print("Testing health endpoint...")
try:
    with urllib.request.urlopen('http://localhost:8000/health') as response:
        data = json.loads(response.read())
        print(f"✓ Health check: {response.status} - {data}")
except Exception as e:
    print(f"✗ Health check failed: {e}")
    exit(1)

# Test document upload
print("\nTesting document upload...")
test_content = b'This is a test Form 16 document for testing upload functionality.'
b64_content = base64.b64encode(test_content).decode('utf-8')

upload_data = {
    'user_id': 'ad1b95a9-cc3f-4dfd-99b8-dc37eaa469fa',
    'file': {
        'document_type': 'form_16',
        'content': b64_content,
        'filename': 'test_form16.txt'
    }
}

try:
    data = json.dumps(upload_data).encode('utf-8')
    req = urllib.request.Request(
        'http://localhost:8000/api/agent/process',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print(f"✓ Upload status: {response.status}")
        print(f"✓ Upload response: {json.dumps(result, indent=2)}")

        # Check if we got a document ID
        if 'document_id' in result:
            document_id = result['document_id']
            print(f"✓ Document ID received: {document_id}")

            # Test extraction
            print("\nTesting document extraction...")
            extract_data = {
                'user_id': 'ad1b95a9-cc3f-4dfd-99b8-dc37eaa469fa',
                'text': 'extract data from form 16'
            }

            extract_req = urllib.request.Request(
                'http://localhost:8000/api/agent/process',
                data=json.dumps(extract_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(extract_req) as extract_response:
                extract_result = json.loads(extract_response.read())
                print(f"✓ Extraction status: {extract_response.status}")
                print(f"✓ Extraction response: {json.dumps(extract_result, indent=2)}")

except Exception as e:
    print(f"✗ Upload test failed: {e}")
    import traceback
    traceback.print_exc()