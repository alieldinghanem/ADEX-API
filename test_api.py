"""
Test script for ADEX Scheduling API
Run this after starting the API with: uvicorn app.main:app --reload
"""

import requests
import json


# Configuration
API_URL = "http://localhost:8000"


def print_separator(title=""):
    """Print a nice separator"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def test_health():
    """Test health endpoint"""
    print("\n🔍 Testing /health endpoint...")
    
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=4)}")
            print("   ✅ Health check PASSED!")
            return True
        else:
            print(f"   ❌ Health check FAILED! Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_root():
    """Test root endpoint"""
    print("\n🔍 Testing / endpoint...")
    
    try:
        response = requests.get(f"{API_URL}/")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=4)}")
            print("   ✅ Root endpoint PASSED!")
            return True
        else:
            print(f"   ❌ Root endpoint FAILED!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_config():
    """Test config endpoint"""
    print("\n🔍 Testing /config endpoint...")
    
    try:
        response = requests.get(f"{API_URL}/config")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Days: {data.get('days', [])}")
            print(f"   Time Slots: {data.get('time_slots', [])}")
            print(f"   GA Population: {data.get('ga_settings', {}).get('population_size', 0)}")
            print("   ✅ Config endpoint PASSED!")
            return True
        else:
            print(f"   ❌ Config endpoint FAILED!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_generate_schedule():
    """Test schedule generation with sample data"""
    print("\n🔍 Testing /generate-schedule endpoint...")
    print("   Creating sample input data...")
    
    # Sample data
    input_data = {
        "semesterId": 1,
        "instructors": [
            {
                "instructorId": 1,
                "userId": "dr-ahmed-123",
                "department": "Computer Science",
                "instructorType": "DOCTOR",
                "isAcademicAdvisor": False,
                "isActive": True,
                "availabilities": [
                    {
                        "availabilityId": 1,
                        "dayOfWeek": "Sunday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 2,
                        "dayOfWeek": "Monday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 3,
                        "dayOfWeek": "Tuesday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 4,
                        "dayOfWeek": "Wednesday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    }
                ],
                "assignedCourses": [
                    {
                        "courseCode": "CS101",
                        "courseName": "Introduction to Programming",
                        "semesterId": 1
                    }
                ]
            },
            {
                "instructorId": 2,
                "userId": "ta-sara-456",
                "department": "Computer Science",
                "instructorType": "TA",
                "isAcademicAdvisor": False,
                "isActive": True,
                "availabilities": [
                    {
                        "availabilityId": 5,
                        "dayOfWeek": "Sunday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 6,
                        "dayOfWeek": "Monday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 7,
                        "dayOfWeek": "Tuesday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    }
                ],
                "assignedCourses": [
                    {
                        "courseCode": "CS101",
                        "courseName": "Introduction to Programming",
                        "semesterId": 1
                    }
                ]
            },
            {
                "instructorId": 3,
                "userId": "ta-omar-789",
                "department": "Computer Science",
                "instructorType": "TA",
                "isAcademicAdvisor": False,
                "isActive": True,
                "availabilities": [
                    {
                        "availabilityId": 8,
                        "dayOfWeek": "Sunday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 9,
                        "dayOfWeek": "Wednesday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    },
                    {
                        "availabilityId": 10,
                        "dayOfWeek": "Thursday",
                        "startTime": "09:00:00",
                        "endTime": "15:00:00",
                        "isAvailable": True
                    }
                ],
                "assignedCourses": [
                    {
                        "courseCode": "CS101",
                        "courseName": "Introduction to Programming",
                        "semesterId": 1
                    }
                ]
            }
        ],
        "courses": [
            {
                "courseCode": "CS101",
                "courseName": "Introduction to Programming",
                "department": "Computer Science",
                "credits": 3,
                "prerequisites": [],
                "enrollmentCount": 80,
                "semesterId": 1
            }
        ],
        "rooms": [
            {
                "roomId": 1,
                "roomNumber": "A101",
                "roomType": "LECTURE_HALL",
                "capacity": 100,
                "isAvailable": True
            },
            {
                "roomId": 2,
                "roomNumber": "LAB201",
                "roomType": "GENERAL_LAB",
                "capacity": 40,
                "isAvailable": True
            },
            {
                "roomId": 3,
                "roomNumber": "LAB202",
                "roomType": "GENERAL_LAB",
                "capacity": 40,
                "isAvailable": True
            },
            {
                "roomId": 4,
                "roomNumber": "LAB203",
                "roomType": "GENERAL_LAB",
                "capacity": 40,
                "isAvailable": True
            }
        ],
        "students": []
    }
    
    try:
        print("   Sending POST request to /generate-schedule...")
        
        response = requests.post(
            f"{API_URL}/generate-schedule",
            json=input_data,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minutes timeout
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n   📊 SCHEDULE GENERATED SUCCESSFULLY!")
            print(f"   ├─ Success: {result.get('success', False)}")
            print(f"   ├─ Message: {result.get('message', 'N/A')}")
            print(f"   ├─ Total Sessions: {result.get('totalSessions', 0)}")
            print(f"   ├─ Total Groups: {result.get('totalGroups', 0)}")
            print(f"   ├─ Fitness Score: {result.get('fitnessScore', 0):.2f}")
            print(f"   └─ Generations Used: {result.get('generationsUsed', 0)}")
            
            # Display sample schedule
            if result.get('groupSchedules'):
                print("\n   📅 SAMPLE GROUP SCHEDULE:")
                for i, group in enumerate(result['groupSchedules'][:2], 1):
                    print(f"\n   Group {i}: {group['groupId']}")
                    print(f"   Course: {group['courseCode']}")
                    print(f"   Total Sessions: {group['totalSessions']}")
                    print("   Sessions:")
                    
                    for session in group['sessions']:
                        print(f"      • {session['sessionType']:8} | "
                              f"{session['dayOfWeek']:9} | "
                              f"{session['timeSlot']:12} | "
                              f"Room {session['roomNumber']:6}")
            
            # Display instructor schedules
            if result.get('instructorSchedules'):
                print("\n   👨‍🏫 INSTRUCTOR SCHEDULES:")
                for instructor in result['instructorSchedules'][:3]:
                    print(f"\n   {instructor['instructorName']} ({instructor['instructorType']})")
                    print(f"   Total Sessions: {instructor['totalSessions']}")
            
            print("\n   ✅ Schedule generation test PASSED!")
            return True
            
        else:
            print(f"   ❌ FAILED! Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Error: Request timeout (took longer than 2 minutes)")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Error: Could not connect to API")
        print("   Make sure the API is running: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print_separator("🚀 ADEX SCHEDULING API - TEST SUITE")
    print("\n   API URL: " + API_URL)
    print("   Starting tests...")
    
    results = {
        "root": False,
        "health": False,
        "config": False,
        "schedule": False
    }
    
    # Run tests
    results["root"] = test_root()
    results["health"] = test_health()
    results["config"] = test_config()
    results["schedule"] = test_generate_schedule()
    
    # Summary
    print_separator("📊 TEST SUMMARY")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n   Tests Passed: {passed}/{total}")
    print("\n   Details:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"      {test_name:15} : {status}")
    
    print_separator()
    
    if passed == total:
        print("\n   🎉 ALL TESTS PASSED! 🎉\n")
        return True
    else:
        print(f"\n   ⚠️  {total - passed} TEST(S) FAILED\n")
        return False


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        exit(1)