"""
In-memory database configuration and setup for Mergington High School API
"""

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from typing import Dict, Any, List, Optional
from copy import deepcopy


class InMemoryCollection:
    """Simple in-memory collection that mimics MongoDB collection interface"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query"""
        if "_id" in query:
            doc = self.data.get(query["_id"])
            if doc:
                result = deepcopy(doc)
                result["_id"] = query["_id"]
                return result
        return None
    
    def find(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Find all documents matching the query"""
        if query is None:
            query = {}
        
        results = []
        for doc_id, doc in self.data.items():
            match = True
            
            # Handle schedule_details.days filter
            if "schedule_details.days" in query:
                days_query = query["schedule_details.days"]
                if "$in" in days_query:
                    required_day = days_query["$in"][0]
                    if required_day not in doc.get("schedule_details", {}).get("days", []):
                        match = False
            
            # Handle start_time filter
            if "schedule_details.start_time" in query and match:
                start_time_query = query["schedule_details.start_time"]
                if "$gte" in start_time_query:
                    required_time = start_time_query["$gte"]
                    actual_time = doc.get("schedule_details", {}).get("start_time", "")
                    if actual_time < required_time:
                        match = False
            
            # Handle end_time filter
            if "schedule_details.end_time" in query and match:
                end_time_query = query["schedule_details.end_time"]
                if "$lte" in end_time_query:
                    required_time = end_time_query["$lte"]
                    actual_time = doc.get("schedule_details", {}).get("end_time", "")
                    if actual_time > required_time:
                        match = False
            
            if match:
                result = deepcopy(doc)
                result["_id"] = doc_id
                results.append(result)
        
        return results
    
    def insert_one(self, document: Dict[str, Any]) -> Any:
        """Insert a single document"""
        doc_id = document.get("_id")
        if doc_id is None:
            raise ValueError("Document must have an _id field")
        
        doc_copy = deepcopy(document)
        doc_copy.pop("_id", None)
        self.data[doc_id] = doc_copy
        return type('obj', (object,), {'inserted_id': doc_id})
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> Any:
        """Update a single document"""
        if "_id" not in query:
            return type('obj', (object,), {'modified_count': 0})
        
        doc_id = query["_id"]
        if doc_id not in self.data:
            return type('obj', (object,), {'modified_count': 0})
        
        doc = self.data[doc_id]
        
        # Handle $push operation
        if "$push" in update:
            for key, value in update["$push"].items():
                if key not in doc:
                    doc[key] = []
                doc[key].append(value)
        
        # Handle $pull operation
        if "$pull" in update:
            for key, value in update["$pull"].items():
                if key in doc and isinstance(doc[key], list):
                    doc[key] = [item for item in doc[key] if item != value]
        
        # Handle $set operation
        if "$set" in update:
            for key, value in update["$set"].items():
                doc[key] = value
        
        return type('obj', (object,), {'modified_count': 1})
    
    def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching the query"""
        if query is None or query == {}:
            return len(self.data)
        return len(self.find(query))
    
    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple aggregation pipeline support"""
        results = []
        
        # Handle the days aggregation pipeline
        for doc_id, doc in self.data.items():
            if "schedule_details" in doc and "days" in doc["schedule_details"]:
                for day in doc["schedule_details"]["days"]:
                    if {"_id": day} not in results:
                        results.append({"_id": day})
        
        # Sort results
        results.sort(key=lambda x: x["_id"])
        return results


# Initialize in-memory collections
activities_collection = InMemoryCollection()
teachers_collection = InMemoryCollection()
announcements_collection = InMemoryCollection()

# Methods


def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plain password against an Argon2 hashed password.

    Returns True when the password matches, False otherwise.
    """
    ph = PasswordHasher()
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        # For any other exception (e.g., invalid hash), treat as non-match
        return False


def init_database():
    """Initialize database if empty"""

    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in initial_activities.items():
            activities_collection.insert_one({"_id": name, **details})

    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in initial_teachers:
            teachers_collection.insert_one(
                {"_id": teacher["username"], **teacher})

    # Initialize announcements if empty
    if announcements_collection.count_documents({}) == 0:
        for announcement in initial_announcements:
            announcements_collection.insert_one(announcement)


# Initial database if empty
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    }
}

initial_teachers = [
    {
        "username": "mrodriguez",
        "display_name": "Ms. Rodriguez",
        "password": hash_password("art123"),
        "role": "teacher"
    },
    {
        "username": "mchen",
        "display_name": "Mr. Chen",
        "password": hash_password("chess456"),
        "role": "teacher"
    },
    {
        "username": "principal",
        "display_name": "Principal Martinez",
        "password": hash_password("admin789"),
        "role": "admin"
    }
]

initial_announcements = [
    {
        "_id": "announcement-1",
        "message": "Activity registration is open until the end of the month. Don't lose your spot!",
        "start_date": "2026-02-01",
        "expiration_date": "2026-02-28",
        "created_by": "principal",
        "created_at": "2026-02-01T08:00:00Z"
    }
]
