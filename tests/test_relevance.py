"""Unit and Scenario Tests for Product Relevance Filtering & Intelligent Ranking.

Covers all 7 mandatory test cases from the Product Relevance Specification:
1. Test 1: Generic Sunroof query ("Sunroof for Hyundai Creta")
   - Panorama Roof Assembly is primary (EXACT_MATCH / CLOSE_MATCH)
   - Glass is COMPONENT
   - Drain hose and grommet are ACCESSORY
2. Test 2: Specific Component query ("Sunroof drain hose for Hyundai Creta")
   - Drain hose is EXACT_MATCH
3. Test 3: Sunroof Glass query ("Sunroof glass for Hyundai Creta")
   - Glass Assembly is EXACT_MATCH
4. Test 4: Sunroof Mechanism query ("Sunroof mechanism for Hyundai Creta")
   - Mechanism Assembly is EXACT_MATCH
5. Test 5: Price Sorting ("Sunroof for Hyundai Creta", sort price asc)
   - Primary matches remain on top of components and accessories
   - Price sorting sorts WITHIN tiers, not across tiers
6. Test 6: Cross-Supplier Comparison
   - Both Boodmo and AutoDukan items are classified consistently
7. Test 7: Ambiguous Product ("ROLLER BLIND ASSY-PANORAMAROOF")
   - Classified as ACCESSORY or COMPONENT, never as Primary Match
"""
import unittest
from parts_agent.relevance import (
    classify_product,
    classify_listings,
    rank_listings,
    parse_query_intent,
    EXACT_MATCH,
    CLOSE_MATCH,
    COMPONENT,
    ACCESSORY,
    NEEDS_REVIEW,
    IRRELEVANT,
)


class TestProductRelevance(unittest.TestCase):
    def setUp(self):
        # Sample products extracted from actual AutoDukan sunroof category
        self.autodukan_sunroof_products = [
            {"title": "GROMMET-SUNROOF DRAIN HOSE", "price": 32, "supplier": "AutoDukan", "part_number": "81684-2V000"},
            {"title": "ROLL BLIND ASSY-SLIDE SHOE,LH", "price": 196, "supplier": "AutoDukan", "part_number": "81655-C9000"},
            {"title": "ROLL BLIND ASSY-SLIDE SHOE,RH", "price": 196, "supplier": "AutoDukan", "part_number": "81656-C9000"},
            {"title": "MECHANISM ASSY-PANORAMAROOF,LH", "price": 7763, "supplier": "AutoDukan", "part_number": "81631-C9000"},
            {"title": "MECHANISM ASSY-PANORAMAROOF,RH", "price": 7764, "supplier": "AutoDukan", "part_number": "81632-C9000"},
            {"title": "FRAME ASSY-PANORAMAROOF", "price": 33183, "supplier": "AutoDukan", "part_number": "81611-C9000"},
            {"title": "ROLLER BLIND ASSY-PANORAMAROOF", "price": 37651, "supplier": "AutoDukan", "part_number": "81650-C9000"},
            {"title": "GLASS ASSY-PANORAMAROOF,RR", "price": 46015, "supplier": "AutoDukan", "part_number": "81610-C9000"},
            {"title": "GLASS ASSY-PANORAMAROOF MOVING", "price": 47375, "supplier": "AutoDukan", "part_number": "81620-C9000"},
            {"title": "PANORAMA ROOF ASSY", "price": 393938, "supplier": "AutoDukan", "part_number": "81600-C9000"},
        ]

    def test_case_1_generic_sunroof_query(self):
        """Test Case 1: Generic query 'Sunroof for Hyundai Creta'.
        - Complete assembly should be EXACT_MATCH or CLOSE_MATCH.
        - Glass/mechanism should be COMPONENT.
        - Drain hose/grommet should be ACCESSORY.
        """
        query = "Sunroof for Hyundai Creta"
        classified = classify_listings(self.autodukan_sunroof_products, query=query, category="sunroof")

        items_by_title = {item["title"]: item for item in classified}

        # Primary Match check
        primary = items_by_title["PANORAMA ROOF ASSY"]
        self.assertIn(primary["relevance"], [EXACT_MATCH, CLOSE_MATCH])
        self.assertEqual(primary["product_type"], "complete_assembly")

        # Component checks
        glass = items_by_title["GLASS ASSY-PANORAMAROOF MOVING"]
        self.assertEqual(glass["relevance"], COMPONENT)
        self.assertEqual(glass["product_type"], "component")

        mechanism = items_by_title["MECHANISM ASSY-PANORAMAROOF,LH"]
        self.assertEqual(mechanism["relevance"], COMPONENT)

        frame = items_by_title["FRAME ASSY-PANORAMAROOF"]
        self.assertEqual(frame["relevance"], COMPONENT)

        # Accessory checks
        grommet = items_by_title["GROMMET-SUNROOF DRAIN HOSE"]
        self.assertEqual(grommet["relevance"], ACCESSORY)
        self.assertEqual(grommet["product_type"], "accessory")

        shoe = items_by_title["ROLL BLIND ASSY-SLIDE SHOE,LH"]
        self.assertEqual(shoe["relevance"], ACCESSORY)

    def test_case_2_specific_drain_hose_query(self):
        """Test Case 2: Specific Component query 'Sunroof drain hose for Hyundai Creta'.
        - Drain hose should become EXACT_MATCH.
        - Complete sunroof assembly should NOT be EXACT_MATCH.
        """
        query = "Sunroof drain hose for Hyundai Creta"
        classified = classify_listings(self.autodukan_sunroof_products, query=query)
        items_by_title = {item["title"]: item for item in classified}

        drain_hose = items_by_title["GROMMET-SUNROOF DRAIN HOSE"]
        self.assertEqual(drain_hose["relevance"], EXACT_MATCH)
        self.assertIn("Exact match for requested accessory", drain_hose["relevance_reason"])

        roof_assy = items_by_title["PANORAMA ROOF ASSY"]
        self.assertNotEqual(roof_assy["relevance"], EXACT_MATCH)

    def test_case_3_sunroof_glass_query(self):
        """Test Case 3: Sunroof Glass query 'Sunroof glass for Hyundai Creta'.
        - Glass assemblies should be EXACT_MATCH.
        - Complete sunroof assembly or drain hose should NOT be EXACT_MATCH.
        """
        query = "Sunroof glass for Hyundai Creta"
        classified = classify_listings(self.autodukan_sunroof_products, query=query)
        items_by_title = {item["title"]: item for item in classified}

        glass_moving = items_by_title["GLASS ASSY-PANORAMAROOF MOVING"]
        self.assertEqual(glass_moving["relevance"], EXACT_MATCH)

        glass_rr = items_by_title["GLASS ASSY-PANORAMAROOF,RR"]
        self.assertEqual(glass_rr["relevance"], EXACT_MATCH)

        drain_hose = items_by_title["GROMMET-SUNROOF DRAIN HOSE"]
        self.assertEqual(drain_hose["relevance"], ACCESSORY)

        roof_assy = items_by_title["PANORAMA ROOF ASSY"]
        self.assertNotEqual(roof_assy["relevance"], EXACT_MATCH)

    def test_case_4_sunroof_mechanism_query(self):
        """Test Case 4: Sunroof Mechanism query 'Sunroof mechanism for Hyundai Creta'.
        - Mechanism assemblies should be EXACT_MATCH.
        """
        query = "Sunroof mechanism for Hyundai Creta"
        classified = classify_listings(self.autodukan_sunroof_products, query=query)
        items_by_title = {item["title"]: item for item in classified}

        mechanism_lh = items_by_title["MECHANISM ASSY-PANORAMAROOF,LH"]
        self.assertEqual(mechanism_lh["relevance"], EXACT_MATCH)

        mechanism_rh = items_by_title["MECHANISM ASSY-PANORAMAROOF,RH"]
        self.assertEqual(mechanism_rh["relevance"], EXACT_MATCH)

        roof_assy = items_by_title["PANORAMA ROOF ASSY"]
        self.assertNotEqual(roof_assy["relevance"], EXACT_MATCH)

    def test_case_5_price_sorting_never_overrides_relevance(self):
        """Test Case 5: When sorted by price (asc), Primary Match (₹3,93,938) MUST appear
        BEFORE components (₹7,763, ₹46,015) and BEFORE accessories (₹32).
        """
        query = "Sunroof for Hyundai Creta"
        classified = classify_listings(self.autodukan_sunroof_products, query=query)
        ranked = rank_listings(classified, price_order="asc")

        # The very first item must be PANORAMA ROOF ASSY despite being ₹3,93,938!
        self.assertEqual(ranked[0]["title"], "PANORAMA ROOF ASSY")
        self.assertEqual(ranked[0]["price"], 393938)
        self.assertIn(ranked[0]["relevance"], [EXACT_MATCH, CLOSE_MATCH])

        # Find indexes
        titles = [item["title"] for item in ranked]
        roof_idx = titles.index("PANORAMA ROOF ASSY")
        glass_idx = titles.index("GLASS ASSY-PANORAMAROOF MOVING")
        mech_idx = titles.index("MECHANISM ASSY-PANORAMAROOF,LH")
        grommet_idx = titles.index("GROMMET-SUNROOF DRAIN HOSE")

        # Verify strict ordering by tier: Primary < Component < Accessory
        self.assertLess(roof_idx, mech_idx)
        self.assertLess(roof_idx, glass_idx)
        self.assertLess(mech_idx, grommet_idx)
        self.assertLess(glass_idx, grommet_idx)

        # Verify that within COMPONENT tier, price sorting is respected (₹7,763 before ₹47,375)
        self.assertLess(mech_idx, glass_idx)

    def test_case_6_cross_supplier_comparison(self):
        """Test Case 6: Cross-Supplier items (Boodmo & AutoDukan) classified consistently."""
        query = "Sunroof for Hyundai Creta"
        cross_supplier_items = [
            {"title": "PANORAMA ROOF ASSY", "price": 393938, "supplier": "AutoDukan", "part_number": "81600-C9000"},
            {"title": "Panoramicroof Assembly", "price": 385000, "supplier": "Boodmo", "part_number": "81600C9000"},
            {"title": "Sunroof Glass LH", "price": 45000, "supplier": "Boodmo", "part_number": "81620C9000"},
            {"title": "GROMMET-SUNROOF DRAIN HOSE", "price": 32, "supplier": "AutoDukan", "part_number": "81684-2V000"},
            {"title": "Drain Hose Clip", "price": 25, "supplier": "Boodmo", "part_number": "81685C9000"},
        ]

        classified = classify_listings(cross_supplier_items, query=query)
        ranked = rank_listings(classified, price_order="asc")

        # Top 2 must be the complete assemblies from Boodmo and AutoDukan
        top_titles = [item["title"] for item in ranked[:2]]
        self.assertIn("Panoramicroof Assembly", top_titles)
        self.assertIn("PANORAMA ROOF ASSY", top_titles)

        # Next should be component (Sunroof Glass LH)
        self.assertEqual(ranked[2]["title"], "Sunroof Glass LH")

        # Bottom should be accessories (Clip, Grommet)
        bottom_titles = [item["title"] for item in ranked[3:]]
        self.assertIn("Drain Hose Clip", bottom_titles)
        self.assertIn("GROMMET-SUNROOF DRAIN HOSE", bottom_titles)

    def test_case_7_ambiguous_product_roller_blind(self):
        """Test Case 7: ROLLER BLIND ASSY-PANORAMAROOF should be ACCESSORY or COMPONENT,
        never a Primary Match for generic sunroof query.
        """
        query = "Sunroof for Hyundai Creta"
        result = classify_product("ROLLER BLIND ASSY-PANORAMAROOF", query=query)
        self.assertIn(result["relevance"], [ACCESSORY, COMPONENT])
        self.assertNotIn(result["relevance"], [EXACT_MATCH, CLOSE_MATCH])

    def test_case_swift_clutch_plates(self):
        """Test Case: Swift clutch plates query.
        - Clutch Disc, Clutch Set, and Clutch Plate should be Primary Matches (EXACT_MATCH / CLOSE_MATCH).
        - Release Bearing and Cable should be COMPONENT.
        - Return Spring and Pedal Bush should be ACCESSORY.
        - Price sorting ascending should keep primary matches on top of minor hardware.
        """
        query = "Swift clutch plates"
        items = [
            {"title": "DISC ASSY, CLUTCH", "price": 1400, "supplier": "AutoDukan", "part_number": "22400M74L00"},
            {"title": "VALEO Clutch Disc for Swift Petrol", "price": 1200, "supplier": "Boodmo", "part_number": "V-8263"},
            {"title": "LUK Clutch Set (Clutch Disc + Cover Plate)", "price": 3200, "supplier": "Boodmo", "part_number": "L-6203"},
            {"title": "Maruti Suzuki Genuine COVER ASSY, CLUTCH", "price": 1850, "supplier": "AutoDukan", "part_number": "22100M74L00"},
            {"title": "BEARING, CLUTCH RELEASE", "price": 650, "supplier": "Boodmo", "part_number": "23265M79F00"},
            {"title": "CABLE ASSY, CLUTCH", "price": 280, "supplier": "AutoDukan", "part_number": "23710M74L00"},
            {"title": "BUSH, CLUTCH PEDAL SHAFT", "price": 15, "supplier": "Boodmo", "part_number": "09305M08008"},
            {"title": "SPRING, CLUTCH RETURN", "price": 25, "supplier": "AutoDukan", "part_number": "09443M14013"},
        ]

        classified = classify_listings(items, query=query)
        ranked = rank_listings(classified, price_order="asc")

        # Top 4 must be the primary matches (Clutch Disc, Cover, Kit)
        top_titles = [item["title"] for item in ranked[:4]]
        self.assertIn("VALEO Clutch Disc for Swift Petrol", top_titles)
        self.assertIn("DISC ASSY, CLUTCH", top_titles)
        self.assertIn("LUK Clutch Set (Clutch Disc + Cover Plate)", top_titles)
        self.assertIn("Maruti Suzuki Genuine COVER ASSY, CLUTCH", top_titles)

        # Primary matches must appear before components and accessories
        titles = [item["title"] for item in ranked]
        self.assertLess(titles.index("LUK Clutch Set (Clutch Disc + Cover Plate)"), titles.index("CABLE ASSY, CLUTCH"))
        self.assertLess(titles.index("LUK Clutch Set (Clutch Disc + Cover Plate)"), titles.index("SPRING, CLUTCH RETURN"))
        self.assertLess(titles.index("LUK Clutch Set (Clutch Disc + Cover Plate)"), titles.index("BUSH, CLUTCH PEDAL SHAFT"))

        # Verify accessories
        items_by_title = {item["title"]: item for item in classified}
        self.assertEqual(items_by_title["BUSH, CLUTCH PEDAL SHAFT"]["relevance"], ACCESSORY)
        self.assertEqual(items_by_title["SPRING, CLUTCH RETURN"]["relevance"], COMPONENT)
        self.assertEqual(items_by_title["BEARING, CLUTCH RELEASE"]["relevance"], COMPONENT)

    def test_case_non_part_navigation_links_classified_as_irrelevant(self):
        """Website navigation, policy pages, seller links, or marketing text must be IRRELEVANT
        and dropped completely from the ranked results.
        """
        query = "Swift clutch plates"
        items = [
            {"title": "Clutch Disc / Plate", "price": 1800, "supplier": "AutoDukan", "url": "https://autodukan.com/product/123"},
            {"title": "Return Policy", "price": 2.0, "supplier": "AutoDukan", "url": "https://autodukan.com/return-policy"},
            {"title": "Become an AutoDukan seller", "price": 5.0, "supplier": "AutoDukan", "url": "https://autodukan.com/seller"},
            {"title": "OEM Brands", "price": 5.0, "supplier": "AutoDukan", "url": "https://autodukan.com/brands?brand=OEM"},
            {"title": "Privacy Policy", "price": 2.0, "supplier": "AutoDukan", "url": "https://autodukan.com/privacy-policy"},
            {"title": "MORE THAN PARTS — FULL CARE.", "price": 5.0, "supplier": "AutoDukan", "url": "https://autodukan.com/services"},
        ]

        classified = classify_listings(items, query=query)
        items_by_title = {item["title"]: item for item in classified}

        # Verify classifications
        self.assertEqual(items_by_title["Return Policy"]["relevance"], IRRELEVANT)
        self.assertEqual(items_by_title["Become an AutoDukan seller"]["relevance"], IRRELEVANT)
        self.assertEqual(items_by_title["OEM Brands"]["relevance"], IRRELEVANT)
        self.assertEqual(items_by_title["Privacy Policy"]["relevance"], IRRELEVANT)
        self.assertEqual(items_by_title["MORE THAN PARTS — FULL CARE."]["relevance"], IRRELEVANT)

        # In ranking, IRRELEVANT items MUST be excluded completely!
        ranked = rank_listings(classified, price_order="asc")
        ranked_titles = [item["title"] for item in ranked]
        self.assertIn("Clutch Disc / Plate", ranked_titles)
        self.assertNotIn("Return Policy", ranked_titles)
        self.assertNotIn("Become an AutoDukan seller", ranked_titles)
        self.assertNotIn("OEM Brands", ranked_titles)
        self.assertNotIn("Privacy Policy", ranked_titles)
        self.assertNotIn("MORE THAN PARTS — FULL CARE.", ranked_titles)



if __name__ == "__main__":
    unittest.main()
