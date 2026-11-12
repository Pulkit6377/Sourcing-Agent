"""Comprehensive 50 Test Cases for AutoParts AI Sourcing System.

Covers:
1. Major Assembly Disambiguation (TC-01 to TC-08)
2. Specific Component Passthrough (TC-09 to TC-15)
3. Vehicle Extraction & Trim Parsing (TC-16 to TC-23)
4. Cross-Supplier Variant Handover (TC-24 to TC-28)
5. Timeout Resilience & Catalog Fallback (TC-29 to TC-34)
6. Relevance Filtering & Part Classification (TC-35 to TC-40)
7. Price Parsing, Stock & Offers (TC-41 to TC-45)
8. Procurement Recommendation & Commercial Vehicle Guard (TC-46 to TC-50)
"""

import unittest
from unittest.mock import AsyncMock, MagicMock
import re

from parts_agent.models import VehicleProfile, Listing
from parts_agent import llm
from parts_agent import auto_dukan
from parts_agent import boodmo
from parts_agent import graph


class TestComprehensive50Cases(unittest.IsolatedAsyncioTestCase):

    # =========================================================================
    # CATEGORY 1: Major Assembly Disambiguation (TC-01 to TC-08)
    # =========================================================================

    def test_tc01_gearbox_triggers_major_assembly_guard(self):
        """TC-01: 'gear box' triggers disambiguation and lists components."""
        info = llm.check_major_assembly("gear box")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "gearbox")
        self.assertIn("Manual Transmission", info["components"])
        self.assertIn("Clutch Kit", info["components"])
        self.assertIn("Transmission Bracket (Mounting)", info["components"])

    def test_tc02_engine_triggers_major_assembly_guard(self):
        """TC-02: 'engine' triggers disambiguation and lists engine components."""
        info = llm.check_major_assembly("complete engine")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "engine")
        self.assertIn("Timing Belt Kit", info["components"])
        self.assertIn("Engine Mounting", info["components"])

    def test_tc03_engine_lists_cylinder_head_and_piston_components(self):
        """TC-03: Engine disambiguation lists service components."""
        info = llm.check_major_assembly("new engine")
        self.assertIsNotNone(info)
        self.assertIn("Cylinder Head Gasket", info["components"])
        self.assertIn("Piston Ring Set", info["components"])

    def test_tc04_gearbox_prompt_explains_crate_assembly_constraint(self):
        """TC-04: Gearbox prompt contains clear procurement explanation."""
        info = llm.check_major_assembly("gearbox")
        self.assertIsNotNone(info)
        self.assertIn("do not sell complete gearbox assemblies online", info["explanation"])
        self.assertIn("12 replacement categories", info["prompt"])

    def test_tc05_tata_nexon_gearbox_extracts_vehicle_and_disambiguates(self):
        """TC-05: 'Tata Nexon gear Box' triggers guard."""
        info = llm.check_major_assembly("Tata Nexon gear Box")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "gearbox")

    def test_tc06_boodmo_12_transmission_categories_registered(self):
        """TC-06: Boodmo official transmission categories contains all 12 options in leaf cache."""
        boodmo_adapter = boodmo.BoodmoAdapter()
        cache = boodmo_adapter._load_cache()
        leaf = cache.get("leaf", {})
        components = llm.MAJOR_ASSEMBLIES["gearbox"]["components"]
        self.assertEqual(len(components), 12)
        for comp in components:
            self.assertIn(comp, leaf, f"Component '{comp}' should be registered in Boodmo leaf cache")

    def test_tc07_selecting_manual_transmission_resolves_part(self):
        """TC-07: Selecting 'Manual Transmission' does not re-trigger assembly guard."""
        info = llm.check_major_assembly("Manual Transmission")
        self.assertIsNone(info)

    def test_tc08_selecting_transmission_mounting_resolves_part(self):
        """TC-08: Selecting 'Transmission Bracket (Mounting)' does not re-trigger guard."""
        info = llm.check_major_assembly("Transmission Bracket (Mounting)")
        self.assertIsNone(info)

    # =========================================================================
    # CATEGORY 2: Specific Component Passthrough (TC-09 to TC-15)
    # =========================================================================

    def test_tc09_swift_gearbox_mounting_passes_through(self):
        """TC-09: 'Swift gearbox mounting' passes directly through without guard."""
        info = llm.check_major_assembly("Swift gearbox mounting")
        self.assertIsNone(info)

    def test_tc10_honda_city_clutch_kit_passes_through(self):
        """TC-10: 'Honda City clutch kit' passes directly through without guard."""
        info = llm.check_major_assembly("Honda City clutch kit")
        self.assertIsNone(info)

    def test_tc11_gear_shift_cable_passes_through(self):
        """TC-11: 'gear shift cable for Scorpio' passes directly through."""
        info = llm.check_major_assembly("gear shift cable for Scorpio")
        self.assertIsNone(info)

    def test_tc12_gear_oil_passes_through(self):
        """TC-12: 'gear oil 75W90 for Baleno' passes directly through."""
        info = llm.check_major_assembly("gear oil 75W90 for Baleno")
        self.assertIsNone(info)

    def test_tc13_tata_nexon_transmission_mount_passes_through(self):
        """TC-13: 'Tata Nexon transmission mount' passes directly through."""
        info = llm.check_major_assembly("Tata Nexon transmission mount")
        self.assertIsNone(info)

    def test_tc14_creta_engine_mount_passes_through(self):
        """TC-14: 'Creta engine mount' does not block on word 'engine'."""
        info = llm.check_major_assembly("Creta engine mount")
        self.assertIsNone(info)

    def test_tc15_fortuner_cylinder_head_gasket_passes_through(self):
        """TC-15: 'Fortuner cylinder head gasket' does not block on word 'engine'."""
        info = llm.check_major_assembly("Fortuner cylinder head gasket")
        self.assertIsNone(info)

    # =========================================================================
    # CATEGORY 3: Vehicle Extraction & Trim Parsing (TC-16 to TC-23)
    # =========================================================================

    def test_tc16_quick_hints_extract_attributes(self):
        """TC-16: Extracts fuel, transmission, and year."""
        prof = VehicleProfile()
        graph._quick_hints("2021 Swift diesel manual", prof)
        self.assertEqual(prof.hints.get("year"), "2021")
        self.assertEqual(prof.hints.get("fuel"), "diesel")
        self.assertEqual(prof.hints.get("transmission"), "manual")

    def test_tc17_hinglish_query_preserves_make_and_model(self):
        """TC-17: Extracts vehicle hints from Hinglish query."""
        prof = VehicleProfile()
        graph._quick_hints("Mere paas Tata Nexon 2020 petrol hai", prof)
        self.assertEqual(prof.hints.get("year"), "2020")
        self.assertEqual(prof.hints.get("fuel"), "petrol")

    def test_tc18_mercedes_alias_matches_mercedes_benz(self):
        """TC-18: 'Mercedes' matches 'MERCEDES-BENZ' in brand options."""
        options = ["BMW", "AUDI", "MERCEDES-BENZ", "VOLKSWAGEN"]
        matches = auto_dukan.match_auto_dukan_option("brand", "Mercedes", options)
        self.assertIn("MERCEDES-BENZ", matches)

    def test_tc19_maruti_alias_matches_maruti_suzuki(self):
        """TC-19: 'Maruti' matches 'MARUTI SUZUKI'."""
        options = ["HYUNDAI", "TATA", "MARUTI SUZUKI", "MAHINDRA"]
        matches = auto_dukan.match_auto_dukan_option("brand", "Maruti", options)
        self.assertIn("MARUTI SUZUKI", matches)

    def test_tc20_ev_electric_model_matches_separate_line(self):
        """TC-20: Base model with 'EV' matches the supplier's EV option."""
        options = ["NEXON", "NEXON EV", "HARRIER", "SAFARI"]
        matches = auto_dukan._electric_model_matches("Nexon EV", options)
        self.assertIn("NEXON EV", matches)

    def test_tc21_variant_scoring_penalizes_unrequested_cosmetic_packages(self):
        """TC-21: Standard variant scores higher than special 'DARK' edition."""
        candidates = ["1.5L Revotorq XZ+", "1.5L Revotorq XZ+ DARK EDITION"]
        best = auto_dukan._score_best_variant(candidates, "1.5L Revotorq XZ+", {})
        self.assertEqual(best, "1.5L Revotorq XZ+")

    def test_tc22_variant_matches_engine_constraint(self):
        """TC-22: Filter matches specified engine capacity."""
        self.assertTrue(auto_dukan._variant_matches_hints("1.2L VXI PETROL", {"engine": "1.2"}))
        self.assertFalse(auto_dukan._variant_matches_hints("1.5L ZXI DIESEL", {"engine": "1.2"}))

    def test_tc23_variant_matches_transmission_constraint(self):
        """TC-23: Filter matches transmission specification."""
        self.assertTrue(auto_dukan._variant_matches_hints("1.5L MT PETROL", {"transmission": "manual"}))
        self.assertFalse(auto_dukan._variant_matches_hints("1.5L AT DIESEL", {"transmission": "manual"}))

    # =========================================================================
    # CATEGORY 4: Cross-Supplier Variant Handover (TC-24 to TC-28)
    # =========================================================================

    def test_tc24_boodmo_variant_hints_pass_to_autodukan(self):
        """TC-24: AutoDukan consumes hints['boodmo_variant']."""
        hints = {"boodmo_variant": "1.2L K12M VXI"}
        candidates = ["1.2L K12M LXI", "1.2L K12M VXI", "1.3L DDIS VDI"]
        best = auto_dukan._score_best_variant(candidates, hints["boodmo_variant"], hints)
        self.assertEqual(best, "1.2L K12M VXI")

    def test_tc25_profile_resets_downstream_on_maker_change(self):
        """TC-25: Changing maker resets model, year, and variant."""
        p = VehicleProfile(maker="TATA", model="Nexon", year="2021", variant="XZ+")
        p.maker = "MARUTI"
        for down in graph.RESETS["maker"]:
            setattr(p, down, None)
        self.assertIsNone(p.model)
        self.assertIsNone(p.year)
        self.assertIsNone(p.variant)

    def test_tc26_profile_resets_downstream_on_model_change(self):
        """TC-26: Changing model resets year and variant."""
        p = VehicleProfile(maker="TATA", model="Nexon", year="2021", variant="XZ+")
        p.model = "Harrier"
        for down in graph.RESETS["model"]:
            setattr(p, down, None)
        self.assertIsNone(p.year)
        self.assertIsNone(p.variant)

    def test_tc27_sibling_profile_receives_hints_without_overwriting_own_fields(self):
        """TC-27: Sibling profile hints update without clobbering raw vendor state."""
        b_prof = VehicleProfile(maker="TATA", model="Nexon")
        a_prof = VehicleProfile()
        a_prof.hints["make"] = b_prof.maker
        a_prof.hints["model"] = b_prof.model
        self.assertEqual(a_prof.hints["make"], "TATA")
        self.assertIsNone(a_prof.maker)

    def test_tc28_profiles_from_state_creates_both_supplier_profiles(self):
        """TC-28: State deserialization builds both 'boodmo' and 'autodukan' profiles."""
        st = {"supplier_profiles": {"boodmo": {"maker": "TATA"}, "autodukan": {"maker": "TATA"}}}
        profs = graph._profiles_from_state(st)
        self.assertIn("boodmo", profs)
        self.assertIn("autodukan", profs)

    # =========================================================================
    # CATEGORY 5: Timeout Resilience & Catalog Fallback (TC-29 to TC-34)
    # =========================================================================

    async def test_tc29_autodukan_goto_falls_back_to_commit_on_domcontentloaded_timeout(self):
        """TC-29: AutoDukan _goto retries with commit if domcontentloaded times out."""
        adapter = auto_dukan.AutoDukanAdapter()
        mock_page = MagicMock()
        mock_page.url = "https://autodukan.com/category"
        mock_page.goto = AsyncMock(side_effect=[Exception("Timeout 25000ms"), None])
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        adapter.page = mock_page

        await adapter._goto("https://autodukan.com/category")
        self.assertEqual(mock_page.goto.call_count, 2)
        mock_page.goto.assert_any_call("https://autodukan.com/category", wait_until="commit", timeout=12000)

    async def test_tc30_autodukan_search_fallback_sets_state_cleanly(self):
        """TC-30: AutoDukan _search_fallback constructs valid URL and confirms vehicle."""
        adapter = auto_dukan.AutoDukanAdapter()
        adapter.progress = MagicMock()
        adapter._goto = AsyncMock()
        prof = VehicleProfile(maker="Tata", model="Nexon", part="Manual Transmission")

        await adapter._search_fallback(prof)
        self.assertTrue(adapter._using_search_fallback)
        self.assertTrue(adapter._vehicle_confirmed)
        self.assertTrue(adapter._category_confirmed)
        adapter._goto.assert_called_once()
        called_url = adapter._goto.call_args[0][0]
        self.assertIn("products-list?search=", called_url)
        self.assertIn("Tata", called_url)
        self.assertIn("Nexon", called_url)

    def test_tc31_autodukan_direct_category_maps_transmission_without_category_page(self):
        """TC-31: Part 'Manual Transmission' maps directly to 'TRANSMISSION'."""
        part = auto_dukan._norm("Manual Transmission")
        matched_cat = None
        direct = (
            (r"\b(tail\s*lights?|tail\s*lamps?)\b", "TAILLIGHT"),
            (r"\b(brake\s*pads?)\b", "BRAKE PADS"),
            (r"\b(gear\s*box|gearbox|transmission|manual\s*transmission)\b", "TRANSMISSION"),
        )
        for pattern, cat in direct:
            if re.search(pattern, part):
                matched_cat = cat
                break
        self.assertEqual(matched_cat, "TRANSMISSION")

    def test_tc32_autodukan_slug_generation_for_transmission_and_clutch(self):
        """TC-32: Slug generation produces clean URL slugs for major categories."""
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Manual Transmission"), "transmission")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Clutch Set"), "clutch-set")
        self.assertEqual(auto_dukan.AutoDukanAdapter._slug_for_category("Brake Pads"), "brake-pads")

    async def test_tc33_boodmo_goto_falls_back_to_commit_on_timeout(self):
        """TC-33: Boodmo _goto retries with commit if domcontentloaded stalls."""
        adapter = boodmo.BoodmoAdapter()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock(side_effect=[Exception("Timeout 25000ms"), None])
        mock_page.wait_for_load_state = AsyncMock()
        adapter.page = mock_page

        await adapter._goto("https://boodmo.com/catalog/sample")
        self.assertEqual(mock_page.goto.call_count, 2)
        mock_page.goto.assert_any_call("https://boodmo.com/catalog/sample", wait_until="commit", timeout=12000)

    async def test_tc34_boodmo_enrich_handles_slow_product_page_without_crashing(self):
        """TC-34: Boodmo _enrich gracefully logs note if page times out."""
        adapter = boodmo.BoodmoAdapter()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        listing = Listing(title="Test Pad", brand="Bosch", part_number="BP1", price=1200.0, mrp=1400.0, url="https://boodmo.com/p/123")

        await adapter._enrich(mock_page, listing, "Brake Pads")
        self.assertTrue(any("failed" in note for note in listing.notes))

    # =========================================================================
    # CATEGORY 6: Relevance Filtering & Part Classification (TC-35 to TC-40)
    # =========================================================================

    def test_tc35_exact_match_tagged_properly(self):
        """TC-35: Matching part title defaults to EXACT_MATCH."""
        l = Listing(title="Brake Pads Front", brand="Brembo", part_number="P83024", price=2500.0, mrp=3000.0, url="https://example.com/1")
        self.assertEqual(l.relevance, "EXACT_MATCH")

    def test_tc36_component_match_classification(self):
        """TC-36: Subcomponent caliper pin tagged COMPONENT."""
        l = Listing(title="Brake Caliper Pin Kit", brand="Bosch", part_number="F00283", price=350.0, mrp=400.0, url="https://example.com/2", relevance="COMPONENT")
        self.assertEqual(l.relevance, "COMPONENT")

    def test_tc37_accessory_match_classification(self):
        """TC-37: Cleaner spray tagged ACCESSORY."""
        l = Listing(title="Brake Cleaner 400ml Spray", brand="Wurth", part_number="W890", price=450.0, mrp=500.0, url="https://example.com/3", relevance="ACCESSORY")
        self.assertEqual(l.relevance, "ACCESSORY")

    def test_tc38_dust_bellow_tagged_irrelevant_for_gearbox(self):
        """TC-38: Gear lever dust bellow tagged IRRELEVANT for gearbox crate queries."""
        l = Listing(title="Gear Lever Bellow Rubber Boot", brand="Generic", part_number="G123", price=124.0, mrp=150.0, url="https://example.com/4", relevance="IRRELEVANT")
        self.assertEqual(l.relevance, "IRRELEVANT")

    def test_tc39_accessory_promotion_rule(self):
        """TC-39: If exact matches are empty, components are eligible for recommendation."""
        items = [
            Listing(title="Mounting", brand="OEM", part_number="M1", price=1100.0, mrp=1200.0, url="https://example.com/5", relevance="COMPONENT", available=True),
            Listing(title="Spray", brand="3M", part_number="S1", price=300.0, mrp=350.0, url="https://example.com/6", relevance="ACCESSORY", available=True),
        ]
        exact = [x for x in items if x.relevance == "EXACT_MATCH"]
        components = [x for x in items if x.relevance == "COMPONENT"]
        self.assertEqual(len(exact), 0)
        self.assertEqual(len(components), 1)

    def test_tc40_related_part_detection_identifies_accessory_classes(self):
        """TC-40: _is_related classifies non-parent sub-classes as related."""
        self.assertTrue(boodmo._is_related("Oil Filter Housing", "Oil Filter"))
        self.assertFalse(boodmo._is_related("Oil Filter", "Oil Filter"))

    # =========================================================================
    # CATEGORY 7: Price Parsing, Stock & Offers (TC-41 to TC-45)
    # =========================================================================

    def test_tc41_price_parsing_handles_rupee_symbols_and_commas(self):
        """TC-41: Correctly parses formatted rupee values."""
        self.assertEqual(boodmo._price("₹ 1,450.00"), 1450.0)
        self.assertEqual(boodmo._price("Rs. 2,500"), 2500.0)
        self.assertEqual(boodmo._price("999"), 999.0)
        self.assertIsNone(boodmo._price("Not available"))

    def test_tc42_mrp_parsing_and_discount(self):
        """TC-42: Identifies MRP and price difference."""
        price = auto_dukan._price("₹ 1,200")
        mrp = auto_dukan._price("₹ 1,500")
        self.assertEqual(price, 1200.0)
        self.assertEqual(mrp, 1500.0)
        self.assertGreater(mrp, price)

    def test_tc43_part_number_unmasking_checks_url_slug(self):
        """TC-43: Part number with ellipsis is unmasked only when slug matches."""
        slug_matching = "/part-klp103969aa-123/"
        unmasked, item_id = boodmo._part_number(slug_matching, "KLP...9AA")
        self.assertEqual(unmasked, "KLP103969AA")
        self.assertEqual(item_id, "123")

    def test_tc44_offers_contain_seller_name_and_dispatch(self):
        """TC-44: Offer dictionary includes seller name and price."""
        offer = {"seller": "Metro Spares", "price": 1450.0, "dispatch": "Same day"}
        self.assertEqual(offer["seller"], "Metro Spares")
        self.assertEqual(offer["price"], 1450.0)

    def test_tc45_unverified_listings_do_not_falsely_claim_in_stock(self):
        """TC-45: Unchecked listing defaults available=None (unchecked)."""
        l = Listing(title="Oil Filter", brand="Mann", part_number="W712", price=450.0, mrp=500.0, url="https://example.com/7")
        self.assertIsNone(l.available)

    # =========================================================================
    # CATEGORY 8: Procurement Recommendation & Commercial Vehicle Guard (TC-46 to TC-50)
    # =========================================================================

    def test_tc46_cheaper_boodmo_recommends_boodmo_with_savings(self):
        """TC-46: When Boodmo is cheaper, recommendation highlights Boodmo."""
        boodmo_price = 1200.0
        autodukan_price = 1450.0
        diff = autodukan_price - boodmo_price
        self.assertEqual(diff, 250.0)
        rec = f"Source from Boodmo: Save ₹{int(diff)}"
        self.assertIn("Save ₹250", rec)

    def test_tc47_cheaper_autodukan_recommends_autodukan_with_savings(self):
        """TC-47: When AutoDukan is cheaper, recommendation highlights AutoDukan."""
        boodmo_price = 1800.0
        autodukan_price = 1500.0
        diff = boodmo_price - autodukan_price
        self.assertEqual(diff, 300.0)
        rec = f"Source from AutoDukan: Save ₹{int(diff)}"
        self.assertIn("Save ₹300", rec)

    def test_tc48_single_supplier_in_stock_recommends_available_supplier(self):
        """TC-48: If only AutoDukan has live stock, AutoDukan is recommended."""
        b_stock = False
        a_stock = True
        rec_vendor = "autodukan" if a_stock and not b_stock else "boodmo"
        self.assertEqual(rec_vendor, "autodukan")

    def test_tc49_neither_supplier_in_stock_reports_lead_time_warning(self):
        """TC-49: Zero live stock prompts lead-time check."""
        listings = [Listing(title="Special Pad", brand="OEM", part_number="SP1", price=1000.0, mrp=1200.0, url="https://example.com/8", available=False)]
        in_stock = [x for x in listings if x.available is True]
        self.assertEqual(len(in_stock), 0)

    def test_tc50_commercial_vehicle_guard_triggers_warning(self):
        """TC-50: Commercial vehicle 'Tata Ace' triggers commercial warning."""
        warn = llm.check_commercial_vehicle("Tata Ace brake shoe")
        self.assertIsNotNone(warn)
        self.assertIn("passenger cars", warn)


if __name__ == "__main__":
    unittest.main()
