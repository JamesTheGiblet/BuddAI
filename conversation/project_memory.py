"""
Project Memory System
Remembers projects, conversations, and context across sessions
"""

import os
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Project:
    """
    Represents a single project with full context
    """
    
    def __init__(self, name: str, project_type: str = 'general', metadata: Dict = None):
        self.name = name
        self.project_type = project_type
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.status = 'active'  # active, paused, completed, archived
        self.metadata = metadata or {}
        
        # Conversations in this project
        self.conversations = []
        
        # Decisions made
        self.decisions = []
        
        # Next steps
        self.next_steps = []
        
        # Related files
        self.files = []
        
        # Tags for organization
        self.tags = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'project_type': self.project_type,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'metadata': self.metadata,
            'conversations': self.conversations,
            'decisions': self.decisions,
            'next_steps': self.next_steps,
            'files': self.files,
            'tags': self.tags
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'Project':
        """Create from dictionary"""
        project = Project(data['name'], data['project_type'], data.get('metadata', {}))
        project.created_at = data.get('created_at', project.created_at)
        project.updated_at = data.get('updated_at', project.updated_at)
        project.status = data.get('status', 'active')
        project.conversations = data.get('conversations', [])
        project.decisions = data.get('decisions', [])
        project.next_steps = data.get('next_steps', [])
        project.files = data.get('files', [])
        project.tags = data.get('tags', [])
        return project
    
    def add_conversation(self, user_message: str, assistant_response: str, metadata: Dict = None):
        """Add a conversation exchange"""
        self.conversations.append({
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'assistant': assistant_response,
            'metadata': metadata or {}
        })
        self.updated_at = datetime.now().isoformat()
    
    def add_decision(self, decision: str, reasoning: str = None):
        """Record a decision"""
        self.decisions.append({
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'reasoning': reasoning or ''
        })
        self.updated_at = datetime.now().isoformat()
    
    def add_next_step(self, step: str, priority: str = 'medium'):
        """Add a next step"""
        self.next_steps.append({
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'priority': priority,
            'completed': False
        })
        self.updated_at = datetime.now().isoformat()
    
    def complete_step(self, step_index: int):
        """Mark a step as completed"""
        if 0 <= step_index < len(self.next_steps):
            self.next_steps[step_index]['completed'] = True
            self.next_steps[step_index]['completed_at'] = datetime.now().isoformat()
            self.updated_at = datetime.now().isoformat()
    
    def add_file(self, filepath: str, description: str = None):
        """Add a related file"""
        self.files.append({
            'filepath': filepath,
            'description': description or '',
            'added_at': datetime.now().isoformat()
        })
        self.updated_at = datetime.now().isoformat()
    
    def add_tag(self, tag: str):
        """Add a tag"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now().isoformat()
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        summary = f"📁 **{self.name}** ({self.project_type})\n"
        summary += f"Status: {self.status}\n"
        summary += f"Created: {self.created_at[:10]}\n"
        summary += f"Updated: {self.updated_at[:10]}\n\n"
        
        if self.conversations:
            summary += f"💬 Conversations: {len(self.conversations)}\n"
        
        if self.decisions:
            summary += f"✅ Decisions: {len(self.decisions)}\n"
        
        if self.next_steps:
            pending = len([s for s in self.next_steps if not s['completed']])
            summary += f"📋 Next steps: {pending} pending\n"
        
        if self.files:
            summary += f"📄 Files: {len(self.files)}\n"
        
        if self.tags:
            summary += f"🏷️  Tags: {', '.join(self.tags)}\n"
        
        return summary

    def get_timeline(self) -> str:
        """Generate a chronological timeline of project events"""
        events = []
        
        # Add creation
        events.append({
            'timestamp': self.created_at,
            'type': '✨ Created',
            'description': f"Project '{self.name}' started"
        })
        
        # Add conversations
        for conv in self.conversations:
            events.append({
                'timestamp': conv['timestamp'],
                'type': '💬 Chat',
                'description': conv['user'][:50] + "..." if len(conv['user']) > 50 else conv['user']
            })
            
        # Add decisions
        for dec in self.decisions:
            events.append({
                'timestamp': dec['timestamp'],
                'type': '✅ Decision',
                'description': dec['decision']
            })
            
        # Add next steps
        for step in self.next_steps:
            events.append({
                'timestamp': step['timestamp'],
                'type': '📋 Task Added',
                'description': step['step']
            })
            if step.get('completed'):
                events.append({
                    'timestamp': step['completed_at'],
                    'type': '🏁 Task Done',
                    'description': step['step']
                })
                
        # Add files
        for f in self.files:
            events.append({
                'timestamp': f['added_at'],
                'type': '📄 File',
                'description': f.get('filepath', 'Unknown file')
            })
            
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        # Format output
        output = [f"📅 Timeline for {self.name}\n"]
        
        current_date = ""
        for event in events:
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(event['timestamp'])
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except:
                date_str = "Unknown Date"
                time_str = "--:--"
            
            if date_str != current_date:
                output.append(f"\n📅 {date_str}")
                output.append("-" * 20)
                current_date = date_str
            
            output.append(f"  {time_str} | {event['type']}: {event['description']}")
            
        return "\n".join(output)


class ProjectMemory:
    """
    Manages project memory across sessions
    
    Features:
    - Save/load projects
    - Fuzzy search by name
    - Track conversations per project
    - Link decisions and files
    - Cross-project search
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.expanduser('~'), '.buddai', 'projects.db')
        
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # In-memory cache
        self.cache = {}
    
    def _init_database(self):
        """Initialize SQLite database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                name TEXT PRIMARY KEY,
                project_type TEXT,
                created_at TEXT,
                updated_at TEXT,
                status TEXT,
                metadata TEXT,
                conversations TEXT,
                decisions TEXT,
                next_steps TEXT,
                files TEXT,
                tags TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_project(self, project: Project):
        """Save project to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = project.to_dict()
        
        cursor.execute('''
            INSERT OR REPLACE INTO projects 
            (name, project_type, created_at, updated_at, status, metadata, 
             conversations, decisions, next_steps, files, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['project_type'],
            data['created_at'],
            data['updated_at'],
            data['status'],
            json.dumps(data['metadata']),
            json.dumps(data['conversations']),
            json.dumps(data['decisions']),
            json.dumps(data['next_steps']),
            json.dumps(data['files']),
            json.dumps(data['tags'])
        ))
        
        conn.commit()
        conn.close()
        
        # Update cache
        self.cache[project.name] = project
        
        logger.info(f"Saved project: {project.name}")
    
    def load_project(self, name: str) -> Optional[Project]:
        """Load project from database"""
        
        # Check cache first
        if name in self.cache:
            return self.cache[name]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects WHERE name = ?', (name,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            data = {
                'name': row[0],
                'project_type': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'status': row[4],
                'metadata': json.loads(row[5]),
                'conversations': json.loads(row[6]),
                'decisions': json.loads(row[7]),
                'next_steps': json.loads(row[8]),
                'files': json.loads(row[9]),
                'tags': json.loads(row[10])
            }
            
            project = Project.from_dict(data)
            self.cache[name] = project
            return project
        
        return None
    
    def delete_project(self, name: str) -> bool:
        """Delete project"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM projects WHERE name = ?', (name,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if name in self.cache:
            del self.cache[name]
        
        logger.info(f"Deleted project: {name}")
        return deleted
    
    def list_projects(self, status: str = None) -> List[Project]:
        """List all projects"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM projects WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT * FROM projects')
        
        rows = cursor.fetchall()
        conn.close()
        
        projects = []
        for row in rows:
            data = {
                'name': row[0],
                'project_type': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'status': row[4],
                'metadata': json.loads(row[5]),
                'conversations': json.loads(row[6]),
                'decisions': json.loads(row[7]),
                'next_steps': json.loads(row[8]),
                'files': json.loads(row[9]),
                'tags': json.loads(row[10])
            }
            projects.append(Project.from_dict(data))
        
        return projects
    
    def search_projects(self, query: str) -> List[Tuple[Project, float]]:
        """
        Fuzzy search for projects
        
        Returns:
            List of (project, score) tuples sorted by relevance
        """
        
        projects = self.list_projects()
        results = []
        
        query_lower = query.lower()
        
        for project in projects:
            score = 0.0
            
            # Exact match
            if project.name.lower() == query_lower:
                score = 1.0
            
            # Name contains query
            elif query_lower in project.name.lower():
                score = 0.8
            
            # Type match
            elif query_lower in project.project_type.lower():
                score = 0.6
            
            # Tag match
            elif any(query_lower in tag.lower() for tag in project.tags):
                score = 0.7
            
            # Partial word match
            elif any(query_lower in word.lower() for word in project.name.split()):
                score = 0.5
            
            if score > 0:
                results.append((project, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def get_recent_projects(self, n: int = 5) -> List[Project]:
        """Get most recently updated projects"""
        
        projects = self.list_projects()
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects[:n]
    
    def get_project_by_type(self, project_type: str) -> List[Project]:
        """Get all projects of a specific type"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects WHERE project_type = ?', (project_type,))
        rows = cursor.fetchall()
        conn.close()
        
        projects = []
        for row in rows:
            data = {
                'name': row[0],
                'project_type': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'status': row[4],
                'metadata': json.loads(row[5]),
                'conversations': json.loads(row[6]),
                'decisions': json.loads(row[7]),
                'next_steps': json.loads(row[8]),
                'files': json.loads(row[9]),
                'tags': json.loads(row[10])
            }
            projects.append(Project.from_dict(data))
        
        return projects


# Global instance
_project_memory = None

def get_project_memory() -> ProjectMemory:
    """Get or create global project memory"""
    global _project_memory
    if _project_memory is None:
        _project_memory = ProjectMemory()
    return _project_memory