"""Negative and boundary tests for invalid, missing, or ambiguous input."""
from __future__ import annotations

import sys
from pathlib import Path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from parts_agent import boodmo, graph, llm, variants
from parts_agent.models import VehicleProfile


class NegativeAnswerMatchingTests(unittest.TestCase):
    def test_empty_unmatched_and_ambiguous_answers_are_rejected_locally(self):
        self.assertIsNone(llm.match_option_locally("", ["AT", "MT"]))
        self.assertIsNone(llm.match_option_locally("spaceship", ["Tata", "Mahindra"]))
        self.assertIsNone(llm.match_option_locally("AT", ["AT", "AT"]))

    def test_invalid_gemini_indexes_are_rejected(self):
        for index in (0, 3):
            with self.subTest(index=index), patch.object(
                llm, "generate", return_value=SimpleNamespace(parsed=llm.OptionChoice(index=index))
            ):
                self.assertEqual(
                    llm.match_option("unclear wording", "Choose a make", ["Tata", "Mahindra"]),
                    (None, False),
                )

    def test_gemini_matching_failure_falls_back_to_no_choice(self):
        with patch.object(llm, "generate", side_effect=RuntimeError("service unavailable")):
            self.assertEqual(
                llm.match_option("unclear wording", "Choose a make", ["Tata", "Mahindra"]),
                (None, False),
            )

    def test_unmatched_hint_does_not_select_a_vehicle_option(self):
        profile = VehicleProfile()
        need = boodmo.BoodmoAdapter()._match_or_ask(
            "maker", "not a car make", ["Tata", "Mahindra", "Maruti"], "Which make?", profile
        )
        self.assertEqual(profile.maker, None)
        self.assertEqual(need.field, "maker")
        self.assertLessEqual(len(need.options), 4)


class NegativeConversationTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_year_answer_repeats_question_without_mutating_profile(self):
        profile = VehicleProfile(maker="Tata", model="Harrier")
        state = {
            "profile": profile.to_dict(),
            "pending": {"field": "year", "question": "Which year?", "options": ["2020", "2021"]},
            "answer": "1890",
        }
        config = {"configurable": {"thread_id": "negative-test"}}
        with patch.object(graph.llm, "match_option", return_value=(None, False)):
            result = await graph.interpret(state, config)

        self.assertEqual(result["profile"]["year"], None)
        self.assertEqual(result["pending"]["field"], "year")
        self.assertIn("didn't catch that", result["pending"]["note"])
        self.assertIsNone(result["turns"][0]["resolved"])

    async def test_dont_know_year_keeps_search_blocked_and_explains_what_is_needed(self):
        state = {
            "profile": VehicleProfile(model="Harrier").to_dict(),
            "pending": {"field": "year", "question": "Which year?", "options": ["2020", "2021"]},
            "answer": "pata nahi",
        }
        result = await graph.interpret(state, {"configurable": {"thread_id": "negative-test"}})

        self.assertEqual(result["pending"]["field"], "year")
        self.assertIn("model year", result["pending"]["note"])
        self.assertIsNone(result["profile"]["year"])

    async def test_variant_unknown_is_marked_skipped_so_another_attribute_can_be_asked(self):
        state = {
            "profile": VehicleProfile().to_dict(),
            "pending": {"field": "variant_attr", "attr": "fuel", "question": "Fuel?",
                        "options": ["DIESEL", "PETROL"]},
            "answer": "not sure",
        }
        result = await graph.interpret(state, {"configurable": {"thread_id": "negative-test"}})

        self.assertEqual(result["profile"]["variant_filters"]["fuel"], variants.SKIP)
        self.assertIsNone(result["pending"])
        self.assertEqual(result["turns"][0]["resolved"], "unknown")

    async def test_cancel_stops_the_pending_search(self):
        state = {
            "profile": VehicleProfile().to_dict(),
            "pending": {"field": "year", "question": "Which year?", "options": ["2020"]},
            "answer": "band karo",
        }
        result = await graph.interpret(state, {"configurable": {"thread_id": "negative-test"}})

        self.assertTrue(result["cancelled"])
        self.assertIsNone(result["pending"])
        self.assertEqual(result["turns"][0]["resolved"], "cancel")


class NegativeDataHandlingTests(unittest.TestCase):
    def test_empty_or_malformed_catalogue_values_do_not_raise(self):
        self.assertIsNone(boodmo._price("no price"))
        self.assertEqual(boodmo._part_number("/not-a-product/", "masked"), ("masked", ""))
        self.assertEqual(variants.parse_label("")["spec"], "STANDARD")
        self.assertEqual(variants.apply_filters([], {"fuel": "DIESEL"}), [])

    def test_empty_results_and_failed_searches_do_not_recommend_products(self):
        profile = VehicleProfile(maker="Tata", model="Harrier", year="2021", variant="XZ",
                                 category="Oil Filter")
        empty = graph.summarize(profile, {"status": "ok", "listings": [], "message": ""})
        failed = graph.summarize(profile, {"status": "failed", "message": "catalog unavailable"})

        self.assertIn("Boodmo lists 0 parts", empty)
        self.assertIn("None of them has a seller with stock", empty)
        self.assertIn("catalog unavailable", failed)
        self.assertIn("I won't suggest a part I can't verify", failed)


if __name__ == "__main__":
    unittest.main()
