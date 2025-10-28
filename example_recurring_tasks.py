"""
Example usage of the Recurring Tasks API

This script demonstrates how to create and manage recurring tasks
using the Family AI Assistant API.

To run this example:
1. Ensure the API server is running
2. Update the BASE_URL if needed
3. Create test users and family first
4. Run: python example_recurring_tasks.py
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Any

BASE_URL = "http://localhost:8000"  # Update if different


def create_recurring_pattern(pattern_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new recurring pattern"""
    response = requests.post(f"{BASE_URL}/recurring-patterns", json=pattern_data)
    response.raise_for_status()
    return response.json()


def get_recurring_patterns(family_id: int) -> list:
    """Get all recurring patterns for a family"""
    response = requests.get(f"{BASE_URL}/recurring-patterns", params={"family_id": family_id})
    response.raise_for_status()
    return response.json()


def generate_tasks(pattern_id: int, days_ahead: int = 30) -> list:
    """Generate task instances for a pattern"""
    response = requests.post(
        f"{BASE_URL}/recurring-patterns/{pattern_id}/generate",
        params={"days_ahead": days_ahead}
    )
    response.raise_for_status()
    return response.json()


def get_pattern_tasks(pattern_id: int, include_completed: bool = False) -> list:
    """Get all tasks for a recurring pattern"""
    response = requests.get(
        f"{BASE_URL}/recurring-patterns/{pattern_id}/tasks",
        params={"include_completed": include_completed}
    )
    response.raise_for_status()
    return response.json()


def main():
    # Example 1: Weekly class on Sundays at 4 PM
    print("=" * 60)
    print("Example 1: Creating weekly Sunday class at 4 PM")
    print("=" * 60)
    
    weekly_class = {
        "family_id": 1,  # Update with your family_id
        "title": "Take Sarah to Ballet Class",
        "description": "Drive Sarah to ballet at the community center",
        "frequency": "weekly",
        "interval": 1,
        "by_day": [6],  # Sunday (0=Monday, 6=Sunday)
        "start_time_hour": 16,
        "start_time_minute": 0,
        "duration_minutes": 60,
        "start_date": datetime.now().isoformat(),
        "end_date": None,
        "default_assignee_user_id": 2,  # Update with your user_id
        "created_by_user_id": 1,  # Update with your user_id
        "is_active": True,
        "meta": {
            "location": "Community Center",
            "notes": "Bring water bottle and ballet shoes"
        }
    }
    
    try:
        pattern = create_recurring_pattern(weekly_class)
        print(f"✓ Created pattern #{pattern['id']}: {pattern['title']}")
        print(f"  Frequency: {pattern['frequency']}")
        print(f"  Days: {pattern['by_day']}")
        print(f"  Time: {pattern['start_time_hour']:02d}:{pattern['start_time_minute']:02d}")
        print()
    except Exception as e:
        print(f"✗ Error creating pattern: {e}")
        return
    
    # Example 2: Tuesday and Thursday school pickup
    print("=" * 60)
    print("Example 2: Creating Tuesday/Thursday school pickup at 3:30 PM")
    print("=" * 60)
    
    school_pickup = {
        "family_id": 1,
        "title": "School Pickup",
        "description": "Pick up kids from elementary school",
        "frequency": "weekly",
        "interval": 1,
        "by_day": [1, 3],  # Tuesday=1, Thursday=3
        "start_time_hour": 15,
        "start_time_minute": 30,
        "duration_minutes": 30,
        "start_date": datetime.now().isoformat(),
        "end_date": None,
        "default_assignee_user_id": 2,
        "created_by_user_id": 1,
        "is_active": True,
        "meta": {
            "location": "Pine Elementary School",
            "notes": "Early dismissal days"
        }
    }
    
    try:
        pattern2 = create_recurring_pattern(school_pickup)
        print(f"✓ Created pattern #{pattern2['id']}: {pattern2['title']}")
        print(f"  Frequency: {pattern2['frequency']}")
        print(f"  Days: {pattern2['by_day']}")
        print(f"  Time: {pattern2['start_time_hour']:02d}:{pattern2['start_time_minute']:02d}")
        print()
    except Exception as e:
        print(f"✗ Error creating pattern: {e}")
        return
    
    # Example 3: Daily morning routine
    print("=" * 60)
    print("Example 3: Creating daily morning medication reminder")
    print("=" * 60)
    
    daily_task = {
        "family_id": 1,
        "title": "Morning Medication",
        "description": "Take vitamins and supplements",
        "frequency": "daily",
        "interval": 1,
        "by_day": None,
        "start_time_hour": 8,
        "start_time_minute": 0,
        "duration_minutes": 5,
        "start_date": datetime.now().isoformat(),
        "end_date": None,
        "default_assignee_user_id": 1,
        "created_by_user_id": 1,
        "is_active": True,
        "meta": {
            "reminder_type": "medication",
            "notes": "With breakfast"
        }
    }
    
    try:
        pattern3 = create_recurring_pattern(daily_task)
        print(f"✓ Created pattern #{pattern3['id']}: {pattern3['title']}")
        print(f"  Frequency: {pattern3['frequency']}")
        print(f"  Time: {pattern3['start_time_hour']:02d}:{pattern3['start_time_minute']:02d}")
        print()
    except Exception as e:
        print(f"✗ Error creating pattern: {e}")
        return
    
    # Get all patterns for the family
    print("=" * 60)
    print("Retrieving all patterns for family")
    print("=" * 60)
    
    try:
        patterns = get_recurring_patterns(family_id=1)
        print(f"✓ Found {len(patterns)} recurring patterns:")
        for p in patterns:
            print(f"  - #{p['id']}: {p['title']} ({p['frequency']})")
        print()
    except Exception as e:
        print(f"✗ Error getting patterns: {e}")
    
    # Get tasks for the first pattern
    print("=" * 60)
    print(f"Getting tasks for pattern #{pattern['id']}")
    print("=" * 60)
    
    try:
        tasks = get_pattern_tasks(pattern['id'])
        print(f"✓ Found {len(tasks)} task instances:")
        for task in tasks[:5]:  # Show first 5
            print(f"  - Task #{task['id']}: {task['occurrence_date']} at "
                  f"{task['due_at'][:16] if task['due_at'] else 'N/A'} "
                  f"({task['status']})")
        if len(tasks) > 5:
            print(f"  ... and {len(tasks) - 5} more")
        print()
    except Exception as e:
        print(f"✗ Error getting tasks: {e}")
    
    # Generate more tasks (60 days ahead)
    print("=" * 60)
    print(f"Generating more tasks for pattern #{pattern['id']}")
    print("=" * 60)
    
    try:
        new_tasks = generate_tasks(pattern['id'], days_ahead=60)
        print(f"✓ Generated {len(new_tasks)} new task instances")
        print()
    except Exception as e:
        print(f"✗ Error generating tasks: {e}")
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. View tasks at: GET /tasks?family_id=1")
    print("2. Complete a task: POST /tasks/{task_id}/complete")
    print("3. Update a pattern: PUT /recurring-patterns/{pattern_id}")
    print("4. Deactivate a pattern: PATCH /recurring-patterns/{pattern_id}/deactivate")


if __name__ == "__main__":
    main()


