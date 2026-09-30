import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "ngo_impactguide.py"


class GuidedAssistantUITests(unittest.TestCase):
    def create_app(self, db_path: str, extra_env: dict[str, str] | None = None) -> AppTest:
        env = {"NGO_DATABASE_PATH": db_path, **(extra_env or {})}
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        return AppTest.from_file(str(APP_FILE), default_timeout=10).run()

    def test_clarify_search_and_update_preferences_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "test.db")
            app = self.create_app(db_path)
            self.assertFalse(app.exception)

            app.chat_input[0].set_value("I want to support education in India").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("What kind of support" in str(node.value) for node in app.markdown))

            app.chat_input[0].set_value("I would prefer tutoring").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["results"])
            self.assertTrue(any("Pratham Education Foundation" in r["name"] for r in app.session_state["results"]))

            app.chat_input[0].set_value("Change the location to Karnataka").run()
            self.assertFalse(app.exception)
            names = [record["name"] for record in app.session_state["results"]]
            self.assertEqual(names, ["Akshara Foundation"])
            self.assertEqual(app.session_state["preferences"]["program"], "learning support")

    def test_vague_request_asks_for_a_cause(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.create_app(str(Path(temp_dir) / "test.db"))
            app.chat_input[0].set_value("I want to help people").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("What cause would you like to support?" in str(node.value) for node in app.markdown))

    def test_unavailable_local_llm_falls_back_to_grounded_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.create_app(
                str(Path(temp_dir) / "test.db"),
                {"OLLAMA_MODEL": "test-model", "OLLAMA_URL": "http://127.0.0.1:1/api/chat"},
            )
            app.chat_input[0].set_value("I care about older people and healthcare in India").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state["results"])
            self.assertTrue(any("I found" in str(node.value) for node in app.markdown))

    def test_existing_database_receives_new_starter_records_without_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "existing.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """CREATE TABLE ngos (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, causes TEXT NOT NULL,
                    locations TEXT NOT NULL, program_types TEXT NOT NULL,
                    description TEXT NOT NULL, source_url TEXT NOT NULL,
                    source_accessed TEXT, notes TEXT
                )"""
            )
            conn.execute(
                "INSERT INTO ngos (name, causes, locations, program_types, description, source_url, source_accessed, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Personal record", "education", "India", "learning support", "Keep this user record", "https://example.org", "2026-09-28", "local"),
            )
            conn.commit()
            conn.close()

            app = self.create_app(str(db_path))
            app.chat_input[0].set_value("education in India and school meals").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(r["name"] == "The Akshaya Patra Foundation" for r in app.session_state["results"]))

            conn = sqlite3.connect(db_path)
            names = {row[0] for row in conn.execute("SELECT name FROM ngos")}
            conn.close()
            self.assertIn("Personal record", names)
            self.assertIn("Educate Girls", names)

    def test_browse_page_compares_selected_organizations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.create_app(str(Path(temp_dir) / "test.db"))
            app.get_by_key("project_area").set_value("Browse and compare").run()
            self.assertFalse(app.exception)
            app.get_by_key("compare_selection").set_value(["Pratham Education Foundation", "Teach For India"]).run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Side-by-side comparison" in str(node.value) for node in app.subheader))

    def test_local_data_manager_adds_a_record_and_shows_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            app = self.create_app(str(db_path))
            app.get_by_key("project_area").set_value("Manage local data").run()
            for index, value in enumerate([
                "Student Demo NGO",
                "education;children",
                "India",
                "learning support",
                "https://example.org/student-demo",
                "2026-09-28",
            ]):
                app.text_input[index].set_value(value)
            app.text_area[0].set_value("A test record for the local data manager.")
            app.text_area[1].set_value("Automated UI test")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Record saved" in str(node.value) for node in app.success))

            conn = sqlite3.connect(db_path)
            saved = conn.execute("SELECT COUNT(*) FROM ngos WHERE name=?", ("Student Demo NGO",)).fetchone()[0]
            conn.close()
            self.assertEqual(saved, 1)


if __name__ == "__main__":
    unittest.main()
