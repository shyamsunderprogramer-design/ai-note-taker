#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Integrated Features
Tests all new functionality added to AI Note Taker
"""

import requests
import json
import time
import sys
from typing import Dict, List

# Configuration
API_BASE = "http://127.0.0.1:8000"
TEST_RESULTS = []


def test_endpoint(name: str, method: str, endpoint: str, expected_status: int = 200, **kwargs) -> Dict:
    """Test an API endpoint"""
    url = f"{API_BASE}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Endpoint: {method} {endpoint}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10, **kwargs)
        elif method == "POST":
            response = requests.post(url, timeout=10, **kwargs)
        else:
            print(f"[X] Unsupported method: {method}")
            return {"success": False, "error": "Unsupported method"}

        print(f"Status: {response.status_code}")

        if response.status_code == expected_status:
            try:
                data = response.json()
                print(f"[OK] SUCCESS - Response preview:")
                print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
                TEST_RESULTS.append({"name": name, "status": "PASSED"})
                return {"success": True, "data": data}
            except:
                print(f"[OK] SUCCESS - Response: {response.text[:200]}")
                TEST_RESULTS.append({"name": name, "status": "PASSED"})
                return {"success": True, "data": response.text}
        else:
            print(f"[X] FAILED - Expected {expected_status}, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            TEST_RESULTS.append({"name": name, "status": "FAILED"})
            return {"success": False, "error": response.text}

    except requests.exceptions.ConnectionError:
        print(f"[X] FAILED - Cannot connect to backend at {API_BASE}")
        print("Make sure the backend is running: python backend/main.py")
        TEST_RESULTS.append({"name": name, "status": "FAILED", "error": "Connection error"})
        return {"success": False, "error": "Connection error"}
    except Exception as e:
        print(f"[X] FAILED - Error: {e}")
        TEST_RESULTS.append({"name": name, "status": "FAILED", "error": str(e)})
        return {"success": False, "error": str(e)}


def run_all_tests():
    """Run all feature tests"""
    print("\n" + "="*70)
    print("AI NOTE TAKER - COMPREHENSIVE FEATURE TEST SUITE")
    print("="*70)
    print(f"API Base: {API_BASE}")
    print("="*70)

    # ========================================
    # PHASE 1: Core Health Check
    # ========================================
    print("\n\n[PHASE 1] Core Health Check")
    print("-" * 60)

    test_endpoint(
        "Health Check",
        "GET",
        "/health"
    )

    # ========================================
    # PHASE 2: Mock Interview Library
    # ========================================
    print("\n\n[PHASE 2] Mock Interview Library")
    print("-" * 60)

    test_endpoint(
        "Get All Mock Questions",
        "GET",
        "/mock-interview/questions?limit=5"
    )

    test_endpoint(
        "Get Questions by Role (Software Engineer)",
        "GET",
        "/mock-interview/questions?role=software_engineer&limit=5"
    )

    test_endpoint(
        "Get Questions by Company (Google)",
        "GET",
        "/mock-interview/questions?company=Google&limit=5"
    )

    test_endpoint(
        "Get Random Question",
        "GET",
        "/mock-interview/question/random?role=software_engineer"
    )

    test_endpoint(
        "Get Practice Set",
        "GET",
        "/mock-interview/practice-set?role=software_engineer&num_questions=3"
    )

    test_endpoint(
        "Search Questions",
        "GET",
        "/mock-interview/search?query=design&limit=5"
    )

    test_endpoint(
        "Get Library Stats",
        "GET",
        "/mock-interview/stats"
    )

    test_endpoint(
        "Get Companies List",
        "GET",
        "/mock-interview/companies"
    )

    # ========================================
    # PHASE 3: Web Search Integration
    # ========================================
    print("\n\n[PHASE 3] Web Search Integration")
    print("-" * 60)

    test_endpoint(
        "Web Search Status",
        "GET",
        "/search/status"
    )

    # Note: Actual web search requires API key
    print("\n[!] Skipping actual web search (requires PERPLEXITY_API_KEY or BRAVE_API_KEY)")

    # ========================================
    # PHASE 4: Voice Clone Agent
    # ========================================
    print("\n\n[PHASE 4] Voice Clone Agent")
    print("-" * 60)

    test_endpoint(
        "List Voice Models",
        "GET",
        "/voice-clone/models"
    )

    # Create a voice model
    create_result = test_endpoint(
        "Create Voice Model",
        "POST",
        "/voice-clone/create?name=TestVoice"
    )

    if create_result["success"] and "model_id" in create_result.get("data", {}):
        model_id = create_result["data"]["model_id"]

        test_endpoint(
            "Get Voice Model Status",
            "GET",
            f"/voice-clone/{model_id}/status"
        )

        test_endpoint(
            "Synthesize Speech",
            "POST",
            f"/voice-clone/{model_id}/synthesize?text=Hello%20world"
        )

    # ========================================
    # PHASE 5: Shadow Interview Agent
    # ========================================
    print("\n\n[PHASE 5] Shadow Interview Agent")
    print("-" * 60)

    start_result = test_endpoint(
        "Start Shadow Session",
        "POST",
        "/shadow/start?company=Google&role=software_engineer&stage=technical"
    )

    test_endpoint(
        "Process Transcript - Question",
        "POST",
        "/shadow/process?text=Can%20you%20design%20a%20rate%20limiter&speaker=interviewer"
    )

    test_endpoint(
        "Get Shadow Suggestions",
        "GET",
        "/shadow/suggestions"
    )

    test_endpoint(
        "Get Shadow Stats",
        "GET",
        "/shadow/stats"
    )

    test_endpoint(
        "End Shadow Session",
        "POST",
        "/shadow/end"
    )

    # ========================================
    # PHASE 6: Collaboration Mode (Duo)
    # ========================================
    print("\n\n[PHASE 6] Collaboration Mode (Duo)")
    print("-" * 60)

    collab_result = test_endpoint(
        "Create Collaboration Session",
        "POST",
        "/collaboration/create?host_name=TestHost"
    )

    if collab_result["success"] and "session_id" in collab_result.get("data", {}):
        session_id = collab_result["data"]["session_id"]
        join_code = collab_result["data"]["join_code"]
        host_id = collab_result["data"]["host_id"]

        print(f"\n[+] Session created with join code: {join_code}")

        # Join as collaborator
        join_result = test_endpoint(
            "Join Collaboration Session",
            "POST",
            f"/collaboration/join?join_code={join_code}&name=TestCollaborator"
        )

        if join_result["success"] and "participant_id" in join_result.get("data", {}):
            collaborator_id = join_result["data"]["participant_id"]

            test_endpoint(
                "Get Collaboration Status",
                "GET",
                f"/collaboration/status?session_id={session_id}"
            )

            test_endpoint(
                "Send Message (Collaborator)",
                "POST",
                f"/collaboration/message?session_id={session_id}&participant_id={collaborator_id}&text=Try%20using%20a%20token%20bucket%20algorithm&msg_type=suggestion"
            )

            test_endpoint(
                "Get Messages",
                "GET",
                f"/collaboration/messages?session_id={session_id}&participant_id={host_id}"
            )

            test_endpoint(
                "End Collaboration Session",
                "POST",
                f"/collaboration/end?session_id={session_id}&participant_id={host_id}"
            )

    # ========================================
    # PHASE 7: Job Tracker
    # ========================================
    print("\n\n[PHASE 7] Job Tracker")
    print("-" * 60)

    test_endpoint(
        "Get Job Tracker Stats",
        "GET",
        "/job-tracker/stats"
    )

    test_endpoint(
        "Get Job Applications",
        "GET",
        "/job-tracker/applications"
    )

    # ========================================
    # PHASE 8: Meeting Templates
    # ========================================
    print("\n\n[PHASE 8] Meeting Templates")
    print("-" * 60)

    test_endpoint(
        "Get Meeting Templates",
        "GET",
        "/meeting-templates"
    )

    test_endpoint(
        "Get Template Categories",
        "GET",
        "/meeting-templates/categories"
    )

    # ========================================
    # SUMMARY
    # ========================================
    print("\n\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in TEST_RESULTS if r["status"] == "PASSED")
    failed = sum(1 for r in TEST_RESULTS if r["status"] == "FAILED")
    total = len(TEST_RESULTS)

    print(f"\nTotal Tests: {total}")
    print(f"[OK] Passed: {passed}")
    print(f"[X] Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    print("\n" + "-"*70)
    print("Detailed Results:")
    print("-"*70)

    for result in TEST_RESULTS:
        status_icon = "[OK]" if result["status"] == "PASSED" else "[X]"
        print(f"{status_icon} {result['name']}: {result['status']}")
        if result.get('error'):
            print(f"   Error: {result['error'][:100]}")

    print("\n" + "="*70)
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print(f"[!] {failed} test(s) failed. Check errors above.")
    print("="*70)

    return passed == total


if __name__ == "__main__":
    print("Starting Comprehensive Feature Test Suite...")
    print("Make sure the backend is running: python backend/main.py")
    print("")

    # Wait a moment for user to see instructions
    time.sleep(2)

    success = run_all_tests()

    sys.exit(0 if success else 1)
