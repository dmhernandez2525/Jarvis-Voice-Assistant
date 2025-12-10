#!/usr/bin/env python3
"""
Multi-Project Context Management System

Manages multiple projects with conversation trees, allowing:
- Project selection and navigation
- Conversation tree branching and merging
- Context preservation across conversations
- Distance tracking from original goals
- Time travel through conversation history

Author: Claude & Daniel
Created: 2025-12-09
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class ContextManager:
    """Main context management system"""

    def __init__(self, base_path: str = None):
        """Initialize context manager

        Args:
            base_path: Base directory for all projects (default: ~/Desktop/Claude-Projects)
        """
        if base_path is None:
            base_path = os.path.expanduser("~/Desktop/Claude-Projects")

        self.base_path = Path(base_path)
        self.projects_file = self.base_path / "projects.json"
        self.projects_dir = self.base_path / "projects"

        # Create directories if they don't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        # Load or create projects registry
        self.projects = self._load_projects()

    def _load_projects(self) -> Dict:
        """Load projects registry from JSON"""
        if self.projects_file.exists():
            with open(self.projects_file, 'r') as f:
                return json.load(f)
        else:
            # Create default registry
            default = {
                "projects": [],
                "active_project": None,
                "created": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat()
            }
            self._save_projects(default)
            return default

    def _save_projects(self, data: Dict = None):
        """Save projects registry to JSON"""
        if data is None:
            data = self.projects

        data["last_modified"] = datetime.now().isoformat()

        with open(self.projects_file, 'w') as f:
            json.dump(data, f, indent=2)

    def create_project(self, project_id: str, name: str, description: str,
                      root_goal: str, file_location: str) -> Dict:
        """Create a new project

        Args:
            project_id: Unique identifier (slug format)
            name: Display name
            description: Project description
            root_goal: Main objective of the project
            file_location: Path to project files

        Returns:
            Project metadata dict
        """
        project_path = self.projects_dir / project_id
        project_path.mkdir(parents=True, exist_ok=True)

        # Create project structure
        chunks_dir = project_path / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        # Create tree.json
        tree = {
            "project_id": project_id,
            "root_goal": root_goal,
            "created": datetime.now().isoformat(),
            "nodes": {
                "main": {
                    "id": "main",
                    "type": "root",
                    "goal": root_goal,
                    "chunks": [],
                    "children": [],
                    "created": datetime.now().isoformat()
                }
            },
            "current_node": "main",
            "chunk_counter": {"main": 0}
        }

        tree_file = project_path / "tree.json"
        with open(tree_file, 'w') as f:
            json.dump(tree, f, indent=2)

        # Create symlink to actual project files
        files_link = project_path / "files"
        if not files_link.exists():
            try:
                files_link.symlink_to(os.path.expanduser(file_location))
            except:
                pass  # Symlink creation might fail on some systems

        # Add to projects registry
        project_meta = {
            "id": project_id,
            "name": name,
            "description": description,
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "root_goal": root_goal,
            "file_location": file_location,
            "status": "active"
        }

        self.projects["projects"].append(project_meta)

        # Set as active if first project
        if self.projects["active_project"] is None:
            self.projects["active_project"] = project_id

        self._save_projects()

        return project_meta

    def list_projects(self) -> List[Dict]:
        """List all projects"""
        return self.projects["projects"]

    def get_active_project(self) -> Optional[Dict]:
        """Get currently active project"""
        active_id = self.projects["active_project"]
        if active_id is None:
            return None

        for project in self.projects["projects"]:
            if project["id"] == active_id:
                return project

        return None

    def set_active_project(self, project_id: str):
        """Set active project"""
        # Verify project exists
        found = False
        for project in self.projects["projects"]:
            if project["id"] == project_id:
                found = True
                project["last_active"] = datetime.now().isoformat()
                break

        if not found:
            raise ValueError(f"Project '{project_id}' not found")

        self.projects["active_project"] = project_id
        self._save_projects()

    def load_tree(self, project_id: str = None) -> Dict:
        """Load conversation tree for a project

        Args:
            project_id: Project ID (uses active project if None)

        Returns:
            Tree data dict
        """
        if project_id is None:
            project_id = self.projects["active_project"]

        if project_id is None:
            raise ValueError("No active project")

        tree_file = self.projects_dir / project_id / "tree.json"

        if not tree_file.exists():
            raise FileNotFoundError(f"Tree file not found for project '{project_id}'")

        with open(tree_file, 'r') as f:
            return json.load(f)

    def save_tree(self, tree: Dict, project_id: str = None):
        """Save conversation tree for a project"""
        if project_id is None:
            project_id = self.projects["active_project"]

        if project_id is None:
            raise ValueError("No active project")

        tree_file = self.projects_dir / project_id / "tree.json"

        with open(tree_file, 'w') as f:
            json.dump(tree, f, indent=2)

    def create_chunk(self, content: str, node_id: str = None,
                    project_id: str = None) -> str:
        """Create a new conversation chunk

        Args:
            content: Chunk content (markdown)
            node_id: Node to add chunk to (uses current if None)
            project_id: Project ID (uses active if None)

        Returns:
            Chunk filename
        """
        if project_id is None:
            project_id = self.projects["active_project"]

        tree = self.load_tree(project_id)

        if node_id is None:
            node_id = tree["current_node"]

        # Get node
        if node_id not in tree["nodes"]:
            raise ValueError(f"Node '{node_id}' not found")

        node = tree["nodes"][node_id]

        # Generate chunk filename
        prefix = node_id
        counter = tree["chunk_counter"].get(node_id, 0) + 1
        chunk_name = f"{prefix}-{counter:03d}.md"

        # Save chunk
        chunks_dir = self.projects_dir / project_id / "chunks"
        chunk_file = chunks_dir / chunk_name

        chunk_content = f"""# Chunk: {chunk_name}

**Node:** {node_id}
**Goal:** {node["goal"]}
**Created:** {datetime.now().isoformat()}

---

{content}
"""

        with open(chunk_file, 'w') as f:
            f.write(chunk_content)

        # Update tree
        node["chunks"].append(chunk_name)
        tree["chunk_counter"][node_id] = counter
        self.save_tree(tree, project_id)

        return chunk_name

    def create_branch(self, goal: str, parent_node: str = None,
                     branch_id: str = None, project_id: str = None) -> Dict:
        """Create a new conversation branch

        Args:
            goal: Branch goal/objective
            parent_node: Parent node ID (uses current if None)
            branch_id: Branch identifier (auto-generated if None)
            project_id: Project ID (uses active if None)

        Returns:
            New branch node dict
        """
        if project_id is None:
            project_id = self.projects["active_project"]

        tree = self.load_tree(project_id)

        if parent_node is None:
            parent_node = tree["current_node"]

        # Verify parent exists
        if parent_node not in tree["nodes"]:
            raise ValueError(f"Parent node '{parent_node}' not found")

        # Generate branch ID if not provided
        if branch_id is None:
            # Auto-generate from goal
            branch_id = "branch-" + goal.lower().replace(" ", "-")[:20]

            # Ensure unique
            counter = 1
            base_id = branch_id
            while branch_id in tree["nodes"]:
                branch_id = f"{base_id}-{counter}"
                counter += 1

        # Create branch node
        branch = {
            "id": branch_id,
            "type": "branch",
            "parent": parent_node,
            "branched_at": tree["nodes"][parent_node]["chunks"][-1] if tree["nodes"][parent_node]["chunks"] else None,
            "goal": goal,
            "chunks": [],
            "children": [],
            "created": datetime.now().isoformat(),
            "status": "active"
        }

        # Add to tree
        tree["nodes"][branch_id] = branch
        tree["nodes"][parent_node]["children"].append(branch_id)
        tree["current_node"] = branch_id
        tree["chunk_counter"][branch_id] = 0

        self.save_tree(tree, project_id)

        return branch

    def show_tree(self, project_id: str = None, format: str = "text") -> str:
        """Display conversation tree

        Args:
            project_id: Project ID (uses active if None)
            format: Output format ('text' or 'json')

        Returns:
            Formatted tree string
        """
        tree = self.load_tree(project_id)

        if format == "json":
            return json.dumps(tree, indent=2)

        # Text format with ASCII tree
        output = []
        output.append(f"\n{'='*70}")
        output.append(f"CONVERSATION TREE: {tree['project_id']}")
        output.append(f"{'='*70}")
        output.append(f"Root Goal: {tree['root_goal']}")
        output.append(f"Current Node: {tree['current_node']}")
        output.append(f"{'='*70}\n")

        def render_node(node_id: str, indent: int = 0, is_last: bool = True):
            node = tree["nodes"][node_id]

            # Prefix for tree lines
            if indent == 0:
                prefix = ""
            else:
                prefix = "    " * (indent - 1)
                prefix += "└── " if is_last else "├── "

            # Node info
            status_icon = "✓" if node.get("status") == "completed" else "●"
            current_icon = " ← CURRENT" if node_id == tree["current_node"] else ""

            output.append(f"{prefix}{status_icon} {node_id}: {node['goal']}{current_icon}")
            output.append(f"{prefix}   Chunks: {len(node['chunks'])} | Children: {len(node['children'])}")

            # Render children
            for i, child_id in enumerate(node["children"]):
                is_last_child = (i == len(node["children"]) - 1)
                render_node(child_id, indent + 1, is_last_child)

        render_node("main")

        output.append(f"\n{'='*70}\n")

        return "\n".join(output)

    def goto_node(self, node_id: str, project_id: str = None):
        """Navigate to a specific node in the tree

        Args:
            node_id: Target node ID
            project_id: Project ID (uses active if None)
        """
        tree = self.load_tree(project_id)

        if node_id not in tree["nodes"]:
            raise ValueError(f"Node '{node_id}' not found")

        tree["current_node"] = node_id
        self.save_tree(tree, project_id)

        return tree["nodes"][node_id]

    def read_chunk(self, chunk_name: str, project_id: str = None) -> str:
        """Read a conversation chunk

        Args:
            chunk_name: Chunk filename
            project_id: Project ID (uses active if None)

        Returns:
            Chunk content
        """
        if project_id is None:
            project_id = self.projects["active_project"]

        chunk_file = self.projects_dir / project_id / "chunks" / chunk_name

        if not chunk_file.exists():
            raise FileNotFoundError(f"Chunk '{chunk_name}' not found")

        with open(chunk_file, 'r') as f:
            return f.read()


def cli():
    """Command-line interface for context manager"""
    parser = argparse.ArgumentParser(
        description="Multi-Project Context Management System"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Project commands
    project_parser = subparsers.add_parser("project", help="Project management")
    project_subparsers = project_parser.add_subparsers(dest="subcommand")

    # List projects
    project_subparsers.add_parser("list", help="List all projects")

    # Create project
    create_parser = project_subparsers.add_parser("create", help="Create new project")
    create_parser.add_argument("--id", required=True, help="Project ID")
    create_parser.add_argument("--name", required=True, help="Project name")
    create_parser.add_argument("--description", required=True, help="Project description")
    create_parser.add_argument("--goal", required=True, help="Root goal")
    create_parser.add_argument("--location", required=True, help="Project file location")

    # Set active project
    active_parser = project_subparsers.add_parser("use", help="Set active project")
    active_parser.add_argument("project_id", help="Project ID to activate")

    # Show active project
    project_subparsers.add_parser("current", help="Show current active project")

    # Tree commands
    tree_parser = subparsers.add_parser("tree", help="Show conversation tree")
    tree_parser.add_argument("--format", choices=["text", "json"], default="text")
    tree_parser.add_argument("--project", help="Project ID (uses active if not specified)")

    # Navigation commands
    goto_parser = subparsers.add_parser("goto", help="Navigate to a node")
    goto_parser.add_argument("node_id", help="Node ID to navigate to")
    goto_parser.add_argument("--project", help="Project ID (uses active if not specified)")

    # Branch commands
    branch_parser = subparsers.add_parser("branch", help="Create a new branch")
    branch_parser.add_argument("goal", help="Branch goal/objective")
    branch_parser.add_argument("--id", help="Branch ID (auto-generated if not provided)")
    branch_parser.add_argument("--parent", help="Parent node (uses current if not specified)")
    branch_parser.add_argument("--project", help="Project ID (uses active if not specified)")

    # Chunk commands
    chunk_parser = subparsers.add_parser("chunk", help="Chunk management")
    chunk_subparsers = chunk_parser.add_subparsers(dest="subcommand")

    # Create chunk
    create_chunk_parser = chunk_subparsers.add_parser("create", help="Create new chunk")
    create_chunk_parser.add_argument("content", help="Chunk content")
    create_chunk_parser.add_argument("--node", help="Node ID (uses current if not specified)")
    create_chunk_parser.add_argument("--project", help="Project ID (uses active if not specified)")

    # Read chunk
    read_chunk_parser = chunk_subparsers.add_parser("read", help="Read a chunk")
    read_chunk_parser.add_argument("chunk_name", help="Chunk filename")
    read_chunk_parser.add_argument("--project", help="Project ID (uses active if not specified)")

    args = parser.parse_args()

    # Initialize context manager
    cm = ContextManager()

    # Execute commands
    if args.command == "project":
        if args.subcommand == "list":
            projects = cm.list_projects()
            print(f"\n{'='*70}")
            print("PROJECTS")
            print(f"{'='*70}")
            for project in projects:
                active = " ← ACTIVE" if project["id"] == cm.projects["active_project"] else ""
                print(f"\n{project['id']}{active}")
                print(f"  Name: {project['name']}")
                print(f"  Goal: {project['root_goal']}")
                print(f"  Status: {project['status']}")
                print(f"  Location: {project['file_location']}")
            print(f"\n{'='*70}\n")

        elif args.subcommand == "create":
            project = cm.create_project(
                args.id, args.name, args.description,
                args.goal, args.location
            )
            print(f"✓ Created project: {project['name']} ({project['id']})")

        elif args.subcommand == "use":
            cm.set_active_project(args.project_id)
            print(f"✓ Switched to project: {args.project_id}")

        elif args.subcommand == "current":
            project = cm.get_active_project()
            if project:
                print(f"\nActive project: {project['name']} ({project['id']})")
                print(f"Goal: {project['root_goal']}")
                print(f"Location: {project['file_location']}\n")
            else:
                print("No active project")

    elif args.command == "tree":
        tree_output = cm.show_tree(args.project, args.format)
        print(tree_output)

    elif args.command == "goto":
        node = cm.goto_node(args.node_id, args.project)
        print(f"✓ Navigated to: {node['id']}")
        print(f"  Goal: {node['goal']}")
        print(f"  Type: {node['type']}")

    elif args.command == "branch":
        branch = cm.create_branch(
            args.goal, args.parent, args.id, args.project
        )
        print(f"✓ Created branch: {branch['id']}")
        print(f"  Goal: {branch['goal']}")
        print(f"  Parent: {branch['parent']}")

    elif args.command == "chunk":
        if args.subcommand == "create":
            chunk_name = cm.create_chunk(args.content, args.node, args.project)
            print(f"✓ Created chunk: {chunk_name}")

        elif args.subcommand == "read":
            content = cm.read_chunk(args.chunk_name, args.project)
            print(content)

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
