#!/usr/bin/env python3
"""
Test script to verify document upload functionality
"""
import requests
import base64
import json

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get('http://localhost:8000/health')
        print(f"✓ Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_document_upload():
    """Test document upload endpoint"""
    print("\nTesting document upload...")

    # Create test file content
    test_content = b'This is a test Form 16 document for testing upload functionality.'
    b64_content = base64.b64encode(test_content).decode('utf-8')

    # Prepare upload request
    upload_data = {
        'user_id': 'ad1b95a9-cc3f-4dfd-99b8-dc37eaa469fa',
        'file': {
            'document_type': 'form_16',
            'content': b64_content,
            'filename': 'test_form16.txt'
        }
    }

    try:
        response = requests.post('http://localhost:8000/api/agent/process', json=upload_data)
        print(f"✓ Upload status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
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

                extract_response = requests.post('http://localhost:8000/api/agent/process', json=extract_data)
                print(f"✓ Extraction status: {extract_response.status_code}")

                if extract_response.status_code == 200:
                    extract_result = extract_response.json()
                    print(f"✓ Extraction response: {json.dumps(extract_result, indent=2)}")
                else:
                    print(f"✗ Extraction failed: {extract_response.text}")

            return True
        else:
            print(f"✗ Upload failed: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Upload test failed: {e}")
        return False

def test_chat_query():
    """Test a regular chat query to ensure general functionality still works"""
    print("\nTesting regular chat query...")

    chat_data = {
        'user_id': 'ad1b95a9-cc3f-4dfd-99b8-dc37eaa469fa',
        'text': 'What is my net worth?'
    }

    try:
        response = requests.post('http://localhost:8000/api/agent/process', json=chat_data)
        print(f"✓ Chat query status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✓ Chat response: {result.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"✗ Chat query failed: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Chat query test failed: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Financial Freedom Copilot - Document Upload Test")
    print("=" * 50)

    # Run tests
    health_ok = test_health()
    upload_ok = test_document_upload() if health_ok else False
    chat_ok = test_chat_query() if health_ok else False

    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"  Health Check: {'PASS' if health_ok else 'FAIL'}")
    print(f"  Document Upload: {'PASS' if upload_ok else 'FAIL'}")
    print(f"  Chat Query: {'PASS' if chat_ok else 'FAIL'}")
    print("=" * 50)

    if health_ok and upload_ok and chat_ok:
        print("✓ All tests passed!")
        exit(0)
    else:
        print("✗ Some tests failed!")
        exit(1)