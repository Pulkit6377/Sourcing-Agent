"""Deterministic unit tests; no network, browser, Gemini key, or microphone needed."""
from __future__ import annotations

import sys
from pathlib import Path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import io
import unittest
import wave
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from parts_agent import boodmo, llm, variants, voice
from parts_agent.graph import (
    _a,
    _after_interpret,
    _after_navigate,
    _after_understand,
    _quick_hints,
    _rupees,
    summarize,
)
from parts_agent.models import Listing, NeedInput, VehicleProfile


class ModelTests(unittest.TestCase):
    def test_vehicle_profile_round_trip_preserves_nested_state(self):
        profile = VehicleProfile(
            part="oil filter",
            maker="Tata",
            model="Harrier",
            year="2021",
            variant_filters={"fuel": "DIESEL"},
            hints={"transmission": "automatic"},
            rejected_years=["2026"],
        )

        restored = VehicleProfile.from_dict(profile.to_dict())

        self.assertEqual(restored, profile)
        self.assertEqual(VehicleProfile.from_dict(None), VehicleProfile())

    def test_need_input_and_listing_are_serializable(self):
        need = NeedInput(field="variant_attr", question="Manual or automatic?",
                         options=["AT", "MT"], attr="transmission", candidate="AT")
        listing = Listing(title="Filter", brand="Tata", part_number="ABC", price=12.5,
                          mrp=15, url="https://example.test/item")

        self.assertEqual(need.to_dict()["candidate"], "AT")
        self.assertEqual(listing.to_dict()["fitment"], "unverified")
        self.assertEqual(listing.to_dict()["offers"], [])


class VariantTests(unittest.TestCase):
    LABELS = [
        "2.0L XZA+ AT/Diesel/BS6",
        "2.0L XZ+ MT/Diesel/KYROTEC TURBOCHARGED/BS6",
        "2.0L XZ+ MT/Diesel/BS6",
        "2.0L XZA+ AT/Petrol/BS6",
        "1.5L XZA+ AT/Petrol/BS6",
    ]

    def test_parse_label_extracts_engine_trim_transmission_fuel_and_specs(self):
        parsed = variants.parse_label(self.LABELS[1])

        self.assertEqual(parsed, {
            "fuel": "DIESEL", "engine": "2.0L", "transmission": "MT",
            "trim": "XZ+", "spec": "KYROTEC TURBOCHARGED", "emission": "BS6",
        })

    def test_spoken_label_and_transmission_questions_use_readable_values(self):
        self.assertEqual(variants.speak_label(self.LABELS[0]), "2.0L XZA plus, automatic, diesel")
        self.assertEqual(variants.question_for("transmission", ["AT", "MT"]),
                         "Is it automatic or manual?")

    def test_filters_and_unknown_filter(self):
        selected = variants.apply_filters(self.LABELS, {"fuel": "DIESEL", "transmission": "MT"})
        self.assertEqual(selected, self.LABELS[1:3])
        self.assertEqual(variants.apply_filters(self.LABELS, {"fuel": variants.SKIP}), self.LABELS)

    def test_hints_match_site_values_and_track_whether_they_were_confirmed(self):
        remaining, applied, source = variants.apply_hints(
            self.LABELS,
            {"transmission": "manual", "mentions": ["XZ plus"]},
        )

        self.assertEqual(applied, {"transmission": "MT", "trim": "XZ+"})
        self.assertEqual(source, {"transmission": "said", "trim": "mention"})
        self.assertEqual(remaining, [self.LABELS[1], self.LABELS[2]])

    def test_next_question_uses_easy_attribute_and_stops_at_short_list(self):
        self.assertEqual(variants.next_question(self.LABELS), ("fuel", ["DIESEL", "PETROL"]))
        self.assertIsNone(variants.next_question(self.LABELS[:3]))

    def test_duplicate_labels_are_removed_and_ambiguous_differences_fall_back(self):
        duplicate = self.LABELS[0]
        self.assertEqual(variants.unique_labels([duplicate, duplicate]), [duplicate])
        self.assertEqual(variants.describe_differences([duplicate, duplicate]), [duplicate, duplicate])


class LlmLocalLogicTests(unittest.TestCase):
    def test_match_option_handles_ordinals_aliases_and_spoken_labels(self):
        options = ["2.0L XZA+ AT/Diesel/BS6", "2.0L XZ+ MT/Diesel/BS6"]

        self.assertEqual(llm.match_option_locally("second one", options), 1)
        self.assertEqual(llm.match_option_locally("automatic", ["AT", "MT"]), 0)
        self.assertEqual(llm.match_option_locally("manual", ["AT", "MT"]), 1)
        self.assertEqual(llm.match_option_locally("automatic", options,
                                                   ["automatic", "manual"]), 0)

    def test_years_are_not_treated_as_option_ordinals(self):
        self.assertEqual(llm.match_option_locally("2021", ["2020", "2021", "2022"]), 1)
        self.assertIsNone(llm.match_option_locally("2", ["2020", "2021", "2022"]))

    def test_yes_no_and_closest_are_deterministic(self):
        self.assertIs(llm.is_yes("haan, that's right"), True)
        self.assertIs(llm.is_yes("nahi"), False)
        self.assertIsNone(llm.is_yes("maybe"))
        self.assertEqual(llm.closest("Hariar", ["Harrier", "Nexon", "Swift"])[0], "Harrier")

    @patch.object(llm, "generate", side_effect=AssertionError("Gemini should not be called"))
    def test_match_option_uses_local_match_without_gemini(self, generate):
        self.assertEqual(llm.match_option("automatic", "Transmission?", ["AT", "MT"]), (0, False))
        generate.assert_not_called()


class BoodmoHelperTests(unittest.TestCase):
    def test_price_parsing_accepts_currency_and_grouping(self):
        self.assertEqual(boodmo._price("₹1,299.50"), 1299.5)
        self.assertEqual(boodmo._price("MRP 899"), 899.0)
        self.assertIsNone(boodmo._price(None))
        self.assertIsNone(boodmo._price("price unavailable"))

    def test_related_part_detection_distinguishes_accessory_classes(self):
        self.assertTrue(boodmo._is_related("Oil Filter Housing", "Oil Filter"))
        self.assertFalse(boodmo._is_related("Brake Pad Set", "Front Brake Pads"))
        self.assertFalse(boodmo._is_related("Oil Filter", "Oil Filter"))

    def test_part_number_is_unmasked_only_when_url_matches_mask(self):
        self.assertEqual(boodmo._part_number("/part-klp103969aa-123/", "KLP...9AA"),
                         ("KLP103969AA", "123"))
        self.assertEqual(boodmo._part_number("/part-othernumber-456/", "KLP...9AA"),
                         ("KLP...9AA", "456"))
        self.assertEqual(boodmo._part_number("/not-a-part/", "ABC"), ("ABC", ""))

    def test_match_or_ask_accepts_site_option_or_returns_nearby_choices(self):
        adapter = boodmo.BoodmoAdapter()
        profile = VehicleProfile()

        self.assertIsNone(adapter._match_or_ask("maker", "Tata", ["Tata", "Mahindra"],
                                                "Which make?", profile))
        self.assertEqual(profile.maker, "Tata")
        need = adapter._match_or_ask("maker", "xyz", ["Tata", "Mahindra"],
                                      "Which make?", VehicleProfile())
        self.assertEqual(need.field, "maker")
        self.assertEqual(need.options[0], "Tata")


class GraphLogicTests(unittest.TestCase):
    def test_quick_hints_extract_only_supported_inline_attributes(self):
        profile = VehicleProfile()
        _quick_hints("Oil filter for Harrier 2021 diesel automatic", profile)
        self.assertEqual(profile.hints, {"year": "2021", "fuel": "diesel", "transmission": "automatic"})

    def test_articles_and_rupee_formatting(self):
        self.assertEqual(_a("oil filter"), "an ")
        self.assertEqual(_a("brake pads"), "")
        self.assertEqual(_rupees(972.0), "₹972")
        self.assertEqual(_rupees(972.5), "₹972.50")

    def test_summary_reports_stock_related_items_and_order_status(self):
        profile = VehicleProfile(category="Oil Filter", maker="Tata", model="Harrier",
                                  year="2021", variant="2.0L XZA+ AT/Diesel/BS6")
        outcome = {
            "status": "ok",
            "message": "",
            "listings": [
                {"match": "exact", "available": True, "brand": "tata", "title": "filter element",
                 "part_number": "KLP103969AA", "price": 972.0,
                 "best_offer": {"seller": "MTC", "stock": "9 in stock", "dispatch": "2 days"},
                 "fitment": "verified"},
                {"match": "related", "available": False, "brand": "tata", "title": "housing",
                 "part_number": "H1", "price": 100.0, "best_offer": None, "fitment": "partial"},
            ],
        }

        summary = summarize(profile, outcome)

        self.assertIn("Cheapest in stock", summary)
        self.assertIn("₹972", summary)
        self.assertIn("left out 1 related part", summary)
        self.assertIn("Nothing has been ordered", summary)

    def test_failed_summary_does_not_recommend_unverified_parts(self):
        profile = VehicleProfile(maker="Tata", model="Harrier", year="2021", variant="XZ")
        summary = summarize(profile, {"status": "failed", "message": "site unavailable"})
        self.assertIn("site unavailable", summary)
        self.assertIn("can't verify", summary)

    def test_graph_routes_pending_answers_errors_and_cancellation(self):
        self.assertEqual(_after_understand({"pending": {"field": "year"}}), "interpret")
        self.assertEqual(_after_understand({}), "navigate")
        self.assertEqual(_after_navigate({"error": "failed"}), "present")
        self.assertEqual(_after_navigate({"pending": {"field": "year"}}), "interpret")
        self.assertEqual(_after_navigate({}), "collect")
        self.assertEqual(_after_interpret({"cancelled": True}), "present")
        self.assertEqual(_after_interpret({"pending": {"field": "year"}}), "interpret")
        self.assertEqual(_after_interpret({}), "navigate")


class VoiceHelperTests(unittest.TestCase):
    def test_wav_duration_and_invalid_input(self):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\0\0" * 8000)

        self.assertEqual(voice._wav_seconds(buf.getvalue()), 0.5)
        self.assertEqual(voice._wav_seconds(b"not a wave"), 0.0)


class AutoDukanHelperTests(unittest.TestCase):
    def test_brand_and_model_matching_with_aliases(self):
        from parts_agent import auto_dukan
        brands = ["MARUTI", "HYUNDAI", "MERCEDES-BENZ", "VW", "MORRIS GARAGES", "TATA"]
        self.assertEqual(auto_dukan.match_auto_dukan_option("brand", "mercedes", brands), ["MERCEDES-BENZ"])
        self.assertEqual(auto_dukan.match_auto_dukan_option("brand", "Mercedes Benz", brands), ["MERCEDES-BENZ"])
        self.assertEqual(auto_dukan.match_auto_dukan_option("brand", "volkswagen", brands), ["VW"])
        self.assertEqual(auto_dukan.match_auto_dukan_option("brand", "mg", brands), ["MORRIS GARAGES"])
        self.assertEqual(auto_dukan.match_auto_dukan_option("brand", "maruti suzuki", brands), ["MARUTI"])

        models = ["A-CLASS", "C-CLASS", "E-CLASS", "HARRIER", "NEXON"]
        self.assertEqual(auto_dukan.match_auto_dukan_option("model", "c class", models), ["C-CLASS"])
        self.assertEqual(auto_dukan.match_auto_dukan_option("model", "C-Class", models), ["C-CLASS"])

    def test_variant_scoring_matches_boodmo_reference(self):
        from parts_agent import auto_dukan
        candidates = [
            "2.0L CAMO XZ / DIESEL",
            "XZA+ DARK AT / DIESEL",
            "2.0L XZA+ AT / DIESEL",
            "2.0L CAMO XZA+ AT / DIESEL",
        ]
        boodmo_ref = "2.0L XZA+ AT/Diesel/BS6"
        best = auto_dukan._score_best_variant(candidates, boodmo_ref, {"transmission": "automatic", "fuel": "diesel"})
        self.assertEqual(best, "2.0L XZA+ AT / DIESEL")

    def test_category_paths_and_whitespace_normalization(self):
        from parts_agent import auto_dukan
        self.assertEqual(auto_dukan.AutoDukanAdapter._path_for_category("Tail Light"), ["LIGHTING", "TAILLIGHT"])
        self.assertEqual(auto_dukan.AutoDukanAdapter._path_for_category("Oil Filter"), ["FILTERS", "OIL FILTER"])

        links = [
            {"text": "TAILLIGHT", "label": "browse taillight", "href": "https://autodukan.com/products/lighting/taillight", "path": "/products/lighting/taillight"},
            {"text": "HEADLIGHT", "label": "browse headlight", "href": "https://autodukan.com/products/lighting/headlight", "path": "/products/lighting/headlight"},
        ]
        link = auto_dukan.AutoDukanAdapter._category_link(links, ["Tail Light"], "/products/")
        self.assertIsNotNone(link)
        self.assertEqual(link["text"], "TAILLIGHT")

    def test_expanded_categories_in_boodmo_and_autodukan(self):
        from parts_agent import auto_dukan, boodmo
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Spark Plug"), "spark-plug")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Wiper Blade"), "wiper-blades")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Car Battery"), "battery")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Clutch Kit"), "clutch-set")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Radiator"), "radiator")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Horn"), "horn")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Manual Transmission"), "transmission")
        self.assertEqual(auto_dukan.AutoDukanAdapter._path_for_category("Manual Transmission"), ["TRANSMISSION"])

        # Test Boodmo category cache has leaf paths
        b = boodmo.BoodmoAdapter()
        cache = b._load_cache()
        leaf = cache.get("leaf", {})
        self.assertIn("Spark Plug", leaf)
        self.assertIn("Wiper Blade", leaf)
        self.assertIn("Car Battery", leaf)
        self.assertIn("Clutch Kit", leaf)
        self.assertIn("Radiator", leaf)
        self.assertIn("Horn", leaf)

    def test_commercial_vehicle_guard(self):
        # Known commercial vehicles should trigger the warning
        self.assertIsNotNone(llm.check_commercial_vehicle("Tata Ace Brake Pads"))
        self.assertIn("commercial vehicle", llm.check_commercial_vehicle("Tata Ace Brake Pads"))
        self.assertIsNotNone(llm.check_commercial_vehicle("Ashok Leyland Dost Filter"))
        self.assertIsNotNone(llm.check_commercial_vehicle("Mahindra Bolero Maxi Truck Clutch"))
        self.assertIsNotNone(llm.check_commercial_vehicle("Pickup truck brake shoe"))

        # Passenger cars should NOT trigger the warning
        self.assertIsNone(llm.check_commercial_vehicle("Mercedes E-Class Headlight", "E-CLASS"))
        self.assertIsNone(llm.check_commercial_vehicle("Audi A4 Brake Pads", "A4"))
        self.assertIsNone(llm.check_commercial_vehicle("Tata Harrier Oil Filter", "HARRIER"))
        self.assertIsNone(llm.check_commercial_vehicle("Hyundai Creta Tail Light", "CRETA"))

    def test_major_assembly_guard(self):
        # Broad assemblies that retail sites do not sell whole should trigger the guard
        gb_check = llm.check_major_assembly("gear box")
        self.assertIsNotNone(gb_check)
        self.assertEqual(gb_check["name"], "gearbox")
        self.assertTrue(any("Mounting" in c for c in gb_check["components"]))
        self.assertEqual(len(gb_check["components"]), 12)

        self.assertIsNotNone(llm.check_major_assembly("gearbox"))
        self.assertIsNotNone(llm.check_major_assembly("transmission"))
        self.assertIsNotNone(llm.check_major_assembly("engine"))

        # Specific components should NOT trigger the assembly guard
        self.assertIsNone(llm.check_major_assembly("Gearbox Mounting"))
        self.assertIsNone(llm.check_major_assembly("gear shift cable"))
        self.assertIsNone(llm.check_major_assembly("gear shifter repair kit"))
        self.assertIsNone(llm.check_major_assembly("transmission fluid"))
        self.assertIsNone(llm.check_major_assembly("engine mount"))
        self.assertIsNone(llm.check_major_assembly("timing belt kit"))
        self.assertIsNone(llm.check_major_assembly("Brake Pads"))
        self.assertIsNone(llm.check_major_assembly("Headlight"))

    def test_boodmo_catalog_offline_resolution(self):
        adapter = boodmo.BoodmoAdapter()

        # 1. Radiator resolution
        profile_rad = VehicleProfile(part="Radiator")
        need = asyncio.run(adapter.resolve_category(profile_rad))
        self.assertIsNone(need)
        self.assertEqual(profile_rad.category, "Radiator")
        self.assertEqual(adapter.category_href, "/catalog/3731-radiator/")
        self.assertIn("Radiator Support", profile_rad.hints.get("alternate_categories", []))

        # 2. Water Pump resolution
        adapter_wp = boodmo.BoodmoAdapter()
        profile_wp = VehicleProfile(part="Water pump")
        need_wp = asyncio.run(adapter_wp.resolve_category(profile_wp))
        self.assertIsNone(need_wp)
        self.assertEqual(profile_wp.category, "Water Pump")
        self.assertEqual(adapter_wp.category_href, "/catalog/3730-water_pump/")

        # 3. Cooling Fan direct catalog match
        adapter_fan = boodmo.BoodmoAdapter()
        profile_fan = VehicleProfile(part="Cooling Fan")
        need_fan = asyncio.run(adapter_fan.resolve_category(profile_fan))
        self.assertIsNone(need_fan)
        self.assertEqual(profile_fan.category, "Cooling Fan")
        self.assertEqual(adapter_fan.category_href, "/catalog/4117-cooling_fan/")

    def test_boodmo_collect_multi_category_fallback(self):
        adapter = boodmo.BoodmoAdapter()
        adapter.category_href = "/catalog/3731-radiator/"
        profile = VehicleProfile(
            part="Radiator",
            maker="HYUNDAI",
            model="ALCAZAR",
            year="2024",
            variant="1.5L AT"
        )
        profile.category = "Radiator"
        profile.hints["alternate_categories"] = ["Radiator Support"]

        # Mock page and DOM methods
        mock_page = MagicMock()
        mock_page.url = "https://boodmo.com/catalog/3731-radiator/12345-hyundai_alcazar/"
        adapter.page = mock_page
        adapter._selected = (profile.variant, mock_page.url)
        adapter._goto = AsyncMock()

        # First call (_read_tiles for primary) returns empty list
        # Second call (_read_tiles for alternate Radiator Support) returns a tile
        tile_found = {
            "title": "Radiator Support Bracket",
            "brand": "MOBIS",
            "number": "64101-A1000",
            "price": 2850,
            "mrp": 3100,
            "href": "/catalog/part-radiator_support_bracket-12345/"
        }
        adapter._read_tiles = AsyncMock(side_effect=[[], [tile_found]])
        adapter._enrich = AsyncMock()
        adapter.page.context.new_page = AsyncMock(return_value=MagicMock(close=AsyncMock()))

        outcome = asyncio.run(adapter.collect(profile))
        self.assertEqual(outcome.status, "ok")
        self.assertEqual(len(outcome.listings), 1)
        self.assertEqual(profile.hints.get("resolved_alternate_category"), "Radiator Support")
        self.assertEqual(outcome.listings[0]["title"], "Radiator Support Bracket")

    def test_boodmo_collect_all_categories_not_listed(self):
        adapter = boodmo.BoodmoAdapter()
        adapter.category_href = "/catalog/3731-radiator/"
        profile = VehicleProfile(
            part="Radiator",
            maker="HYUNDAI",
            model="ALCAZAR",
            year="2024",
            variant="1.5L AT"
        )
        profile.category = "Radiator"
        profile.hints["alternate_categories"] = ["Radiator Support"]

        mock_page = MagicMock()
        mock_page.url = "https://boodmo.com/catalog/3731-radiator/12345-hyundai_alcazar/"
        adapter.page = mock_page
        adapter._selected = (profile.variant, mock_page.url)
        adapter._goto = AsyncMock()
        adapter._read_tiles = AsyncMock(return_value=[])

        outcome = asyncio.run(adapter.collect(profile))
        self.assertEqual(outcome.status, "no_results")
        self.assertIn("This part is not listed in Boodmo's catalogue", outcome.message)
        self.assertIn("Radiator", outcome.message)
        self.assertIn("Radiator Support", outcome.message)


if __name__ == "__main__":
    unittest.main()
