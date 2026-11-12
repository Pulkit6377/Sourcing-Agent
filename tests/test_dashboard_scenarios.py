"""Comprehensive scenario tests for Conversational AI Parts Sourcing Dashboard."""
import io
import unittest
import wave
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from parts_agent.models import Listing, NeedInput, Offer, SearchOutcome, VehicleProfile
from server import app, sse_manager


class DashboardScenarioTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # -------------------------------------------------------------
    # Scenario 1: Customer query with all required information
    # -------------------------------------------------------------
    def test_query_with_complete_information(self):
        """Query containing make, model, year, fuel, transmission."""
        from parts_agent.graph import _quick_hints

        p = VehicleProfile()
        p.part = "oil filter"
        p.maker = "Tata"
        p.model = "Harrier"
        _quick_hints("2021 diesel automatic", p)

        self.assertEqual(p.hints.get("fuel"), "diesel")
        self.assertEqual(p.hints.get("transmission"), "automatic")
        self.assertEqual(p.hints.get("year"), "2021")

    # -------------------------------------------------------------
    # Scenario 2: Query requiring multiple follow-ups
    # -------------------------------------------------------------
    def test_query_requiring_follow_ups(self):
        """NeedInput correctly tracks progression from year -> variant."""
        need_year = NeedInput(
            field="year",
            question="Which year is the Harrier? Boodmo lists 2019 to 2026.",
            options=["2019", "2020", "2021", "2022", "2023"],
            note=None
        )
        self.assertEqual(need_year.field, "year")
        self.assertIn("2021", need_year.options)

        need_attr = NeedInput(
            field="variant_attr",
            attr="transmission",
            question="Is it automatic or manual?",
            options=["AT", "MT"]
        )
        self.assertEqual(need_attr.attr, "transmission")
        self.assertEqual(len(need_attr.options), 2)

    # -------------------------------------------------------------
    # Scenario 3: Two suppliers completing at different times
    # -------------------------------------------------------------
    def test_two_suppliers_completing_incrementally(self):
        """Events are published independently and immediately per supplier."""
        thread_id = "test-incremental-stream"
        q = sse_manager.subscribe(thread_id)

        # Supplier 1 (Boodmo) completes first at t=12s
        boodmo_listings = [
            Listing(
                title="Oil Filter Element",
                brand="Tata",
                part_number="KLP103969AA",
                price=972.0,
                mrp=1050.0,
                url="https://boodmo.com/catalog/part-12345",
                fitment="verified",
                available=True,
                best_offer={"seller": "MSMEE/MTC/1", "stock": "9 in stock", "dispatch": "2 days"}
            ).to_dict()
        ]
        sse_manager.publish(thread_id, {
            "type": "adapter_completed",
            "supplier": "Boodmo",
            "vendor": "boodmo",
            "status": "Completed",
            "products_found": 1,
            "results": boodmo_listings,
            "elapsed_seconds": 12.1
        })

        # Verify Boodmo event is received immediately while AutoDukan is still running
        e1 = q.get_nowait()
        self.assertEqual(e1["type"], "adapter_completed")
        self.assertEqual(e1["supplier"], "Boodmo")
        self.assertEqual(e1["products_found"], 1)

        # Supplier 2 (AutoDukan) completes later at t=16s
        autodukan_listings = [
            Listing(
                title="Tata Harrier Engine Oil Filter",
                brand="Bosch",
                part_number="F002H23741",
                price=850.0,
                mrp=920.0,
                url="https://autodukan.com/products/item-789",
                fitment="unverified",
                available=True,
                best_offer={"seller": "AutoDukan Retail", "stock": "In Stock", "dispatch": "Immediate"}
            ).to_dict()
        ]
        sse_manager.publish(thread_id, {
            "type": "adapter_completed",
            "supplier": "AutoDukan",
            "vendor": "autodukan",
            "status": "Completed",
            "products_found": 1,
            "results": autodukan_listings,
            "elapsed_seconds": 16.4
        })

        # Verify AutoDukan event arrives next
        e2 = q.get_nowait()
        self.assertEqual(e2["type"], "adapter_completed")
        self.assertEqual(e2["supplier"], "AutoDukan")
        self.assertEqual(e2["products_found"], 1)

        sse_manager.unsubscribe(thread_id, q)
        sse_manager.clear(thread_id)

    # -------------------------------------------------------------
    # Scenario 4: One supplier fails while other succeeds
    # -------------------------------------------------------------
    def test_one_supplier_fails_while_other_succeeds(self):
        """Adapter failure does not clear the successful supplier's results."""
        thread_id = "test-partial-failure"
        q = sse_manager.subscribe(thread_id)

        # Boodmo succeeds
        sse_manager.publish(thread_id, {
            "type": "adapter_completed",
            "supplier": "Boodmo",
            "vendor": "boodmo",
            "status": "Completed",
            "products_found": 6,
            "results": [{"title": "Filter", "price": 950.0, "vendor": "boodmo"}],
            "elapsed_seconds": 11.5
        })

        # AutoDukan fails with variant mismatch
        sse_manager.publish(thread_id, {
            "type": "adapter_failed",
            "supplier": "AutoDukan",
            "vendor": "autodukan",
            "status": "Failed",
            "error": "AutoDukan vehicle variant mismatch: variant not in catalog",
            "elapsed_seconds": 14.2
        })

        e_boodmo = q.get_nowait()
        self.assertEqual(e_boodmo["type"], "adapter_completed")

        e_autodukan = q.get_nowait()
        self.assertEqual(e_autodukan["type"], "adapter_failed")
        self.assertIn("variant mismatch", e_autodukan["error"])

        sse_manager.unsubscribe(thread_id, q)
        sse_manager.clear(thread_id)

    # -------------------------------------------------------------
    # Scenario 5: Supplier returning zero products (no_results)
    # -------------------------------------------------------------
    def test_supplier_returning_zero_products(self):
        """Zero products case preserves no_results status and specific message."""
        outcome = SearchOutcome(
            vendor="boodmo",
            status="no_results",
            vehicle_label="Tata Harrier 2021 Diesel AT",
            listings=[],
            source_url="https://boodmo.com/catalog/...",
            message="Boodmo lists no Oil Filter for this vehicle."
        )
        self.assertEqual(outcome.status, "no_results")
        self.assertEqual(len(outcome.listings), 0)
        self.assertIn("lists no", outcome.message)

    # -------------------------------------------------------------
    # Scenario 6: Missing seller, stock, or part number
    # -------------------------------------------------------------
    def test_missing_seller_stock_part_number(self):
        """Missing attributes are kept honest, never invented."""
        listing = Listing(
            title="Generic Filter Housing",
            brand="OEM",
            part_number="ABC...XYZ",
            price=None,  # No price
            mrp=None,
            url="https://boodmo.com/part-123",
            best_offer=None,  # No seller
            available=None,   # Stock unchecked
            notes=["Masked part number"]
        )
        d = listing.to_dict()
        self.assertIsNone(d["price"])
        self.assertIsNone(d["best_offer"])
        self.assertIsNone(d["available"])
        self.assertIn("Masked", d["notes"][0])

    # -------------------------------------------------------------
    # Scenario 7: Product price verification distinction
    # -------------------------------------------------------------
    def test_price_verification_distinction(self):
        """Verified offer price vs unverified listing price."""
        verified_listing = Listing(
            title="Verified Filter",
            brand="Tata",
            part_number="KLP103969AA",
            price=972.0,
            mrp=1050.0,
            url="https://boodmo.com/item/1",
            best_offer={"seller": "MSMEE/MTC/1", "stock": "In Stock", "dispatch": "2 days"},
            available=True,
            fitment="verified"
        )

        unverified_listing = Listing(
            title="Unverified Search Result",
            brand="Tata",
            part_number="F002",
            price=900.0,
            mrp=None,
            url="https://autodukan.com/item/2",
            best_offer=None,
            available=None,
            fitment="unverified"
        )

        self.assertIsNotNone(verified_listing.best_offer)
        self.assertEqual(verified_listing.fitment, "verified")
        self.assertIsNone(unverified_listing.best_offer)
        self.assertEqual(unverified_listing.fitment, "unverified")

    # -------------------------------------------------------------
    # Scenario 8: Voice transcription endpoint
    # -------------------------------------------------------------
    def test_transcription_endpoint(self):
        """POST /api/transcribe accepts audio file and calls transcribe."""
        # Create a synthetic 1-second silent WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 16000)
        wav_bytes = buf.getvalue()

        with patch("parts_agent.voice.transcribe", return_value="oil filter for harrier"):
            resp = self.client.post(
                "/api/transcribe",
                files={"file": ("test.wav", wav_bytes, "audio/wav")},
                data={"context": "Which part do you need?"}
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["text"], "oil filter for harrier")


if __name__ == "__main__":
    unittest.main()
