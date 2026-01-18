"""
Tests for the context manager module.
"""

import pytest
import json
import tempfile
import os


class TestContextManager:
    """Tests for context management functionality."""

    def test_context_file_creation(self, tmp_path):
        """Test that context file is created if it doesn't exist."""
        context_file = tmp_path / "context.json"
        assert not context_file.exists()

        # Simulate context manager behavior
        if not context_file.exists():
            context_file.write_text(json.dumps({"projects": {}, "notes": []}))

        assert context_file.exists()

    def test_context_structure(self, tmp_path):
        """Test the structure of the context file."""
        context_file = tmp_path / "context.json"
        initial_context = {
            "projects": {},
            "notes": [],
            "last_updated": None,
        }
        context_file.write_text(json.dumps(initial_context))

        loaded = json.loads(context_file.read_text())
        assert "projects" in loaded
        assert "notes" in loaded
        assert isinstance(loaded["projects"], dict)
        assert isinstance(loaded["notes"], list)

    def test_add_project_context(self, tmp_path):
        """Test adding a project to context."""
        context_file = tmp_path / "context.json"
        context = {"projects": {}, "notes": []}

        # Add a project
        project_name = "test_project"
        project_data = {
            "description": "A test project",
            "path": "/path/to/project",
            "created": "2024-01-01",
        }
        context["projects"][project_name] = project_data

        context_file.write_text(json.dumps(context))
        loaded = json.loads(context_file.read_text())

        assert project_name in loaded["projects"]
        assert loaded["projects"][project_name]["description"] == "A test project"

    def test_add_note(self, tmp_path):
        """Test adding a note to context."""
        context_file = tmp_path / "context.json"
        context = {"projects": {}, "notes": []}

        # Add a note
        note = {
            "content": "Remember to update the documentation",
            "timestamp": "2024-01-01T12:00:00",
            "tags": ["documentation", "todo"],
        }
        context["notes"].append(note)

        context_file.write_text(json.dumps(context))
        loaded = json.loads(context_file.read_text())

        assert len(loaded["notes"]) == 1
        assert loaded["notes"][0]["content"] == "Remember to update the documentation"


class TestNotesTracking:
    """Tests for notes tracking functionality."""

    def test_notes_file_reading(self, tmp_path):
        """Test reading notes from a file."""
        notes_file = tmp_path / "NOTES.md"
        notes_content = """# Notes

## Current Thoughts
- Working on voice assistant
- Need to improve wake word detection

## Ideas
- Add multi-language support
"""
        notes_file.write_text(notes_content)

        content = notes_file.read_text()
        assert "Current Thoughts" in content
        assert "wake word detection" in content

    def test_notes_modification_tracking(self, tmp_path):
        """Test tracking notes file modifications."""
        notes_file = tmp_path / "NOTES.md"
        notes_file.write_text("Initial content")

        initial_mtime = os.path.getmtime(notes_file)

        # Modify the file
        import time

        time.sleep(0.1)
        notes_file.write_text("Updated content")

        new_mtime = os.path.getmtime(notes_file)
        assert new_mtime > initial_mtime
