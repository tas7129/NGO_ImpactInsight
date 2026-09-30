import unittest

from agent import clarification_needed, parse_preferences, search_records


SAMPLE_RECORDS = [
    {
        "name": "HelpAge India",
        "causes": "elderly;health;livelihoods",
        "locations": "India;multiple states",
        "program_types": "elder care;healthcare;livelihoods;advocacy",
        "source_url": "https://example.org/helpage",
    },
    {
        "name": "The Akshaya Patra Foundation",
        "causes": "education;children;nutrition",
        "locations": "India;multiple states",
        "program_types": "school meals;nutrition;education support",
        "source_url": "https://example.org/meals",
    },
    {
        "name": "State-limited example",
        "causes": "education;children",
        "locations": "India;multiple states",
        "program_types": "learning support",
        "source_url": "https://example.org/education",
    },
]


class PreferenceParsingTests(unittest.TestCase):
    def test_older_people_and_healthcare_do_not_confuse_cause_and_program(self):
        self.assertEqual(
            parse_preferences("I care about older people and healthcare"),
            {"cause": "elderly", "location": "", "program": "healthcare"},
        )

    def test_tutoring_maps_to_learning_support(self):
        self.assertEqual(parse_preferences("I want tutoring") ["program"], "learning support")

    def test_changing_location_preserves_other_preferences(self):
        current = {"cause": "education", "location": "india", "program": "learning support"}
        result = parse_preferences("Change the location to Karnataka", current)
        self.assertEqual(result, {"cause": "education", "location": "karnataka", "program": "learning support"})

    def test_unrelated_substrings_are_not_treated_as_preferences(self):
        self.assertEqual(parse_preferences("show options in India"), {"cause": "", "location": "india", "program": ""})


class AgentWorkflowTests(unittest.TestCase):
    def test_broad_education_request_requires_program_clarification(self):
        prefs = parse_preferences("I want to support education in India")
        self.assertEqual(clarification_needed(prefs, already_clarified=False), "program")

    def test_unrecognized_request_asks_for_a_cause(self):
        self.assertEqual(clarification_needed({"cause": "", "location": "", "program": ""}, False), "cause")

    def test_specific_preferences_return_expected_record(self):
        prefs = {"cause": "education", "location": "india", "program": "school meals"}
        results = search_records(prefs, SAMPLE_RECORDS)
        self.assertEqual([record["name"] for record in results], ["The Akshaya Patra Foundation"])

    def test_state_request_does_not_match_only_broad_multiple_states_label(self):
        prefs = {"cause": "education", "location": "karnataka", "program": "learning support"}
        self.assertEqual(search_records(prefs, SAMPLE_RECORDS), [])

    def test_no_preference_records_all_available_matches(self):
        prefs = {"cause": "elderly", "location": "", "program": "healthcare"}
        self.assertEqual([r["name"] for r in search_records(prefs, SAMPLE_RECORDS)], ["HelpAge India"])


if __name__ == "__main__":
    unittest.main()
