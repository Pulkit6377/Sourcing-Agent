"""Live test for Swift clutch plates parts search across suppliers.

Executes conversational sourcing for Maruti Swift clutch plates,
follows up on vehicle details (year, fuel, variant, category),
extracts products from suppliers, and displays the classified & ranked comparison results.
"""
import asyncio
import json
import logging
from parts_agent.graph import open_session, close_session, Conversation, SESSIONS
from parts_agent.relevance import rank_listings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("test_swift_clutch")


async def run_swift_clutch_test():
    thread_id = "test-swift-clutch-live"
    print("\n=======================================================")
    print("🚀 STARTING AUTOMATED TEST: Swift Clutch Plates Sourcing")
    print("=======================================================\n")

    open_session(thread_id, headless=True)
    convo = Conversation(thread_id)

    query = "Swift clutch plates"
    print(f"Customer Query: '{query}'\n")

    q = await convo.start(query)
    step = 1

    # Automated reply mapping for common questions
    smart_answers = {
        "kind": "Clutch Kit",
        "category": "Clutch Kit",
        "year": "2018",
        "fuel": "petrol",
        "transmission": "manual",
        "variant": "VXI",
    }

    while q and step <= 10:
        question_text = q.get("question") or ""
        field = q.get("field") or ""
        options = q.get("options") or []
        print(f"Step {step} - Agent Question: {question_text}")
        if options:
            print(f"  Options available: {options[:5]} (total {len(options)})")

        # Pick appropriate answer
        chosen_reply = None
        q_lower = question_text.lower()

        if "kind" in q_lower or "clutch pressure plate" in q_lower or field == "category":
            if "Clutch Kit" in options:
                chosen_reply = "Clutch Kit"
            elif options:
                chosen_reply = options[0]
            else:
                chosen_reply = "Clutch Kit"
        elif "year" in q_lower or field == "year":
            # Match 2018 or closest available
            if "2018" in options:
                chosen_reply = "2018"
            elif options:
                chosen_reply = options[0]
            else:
                chosen_reply = "2018"
        elif "fuel" in q_lower or field == "fuel":
            petrol_opts = [opt for opt in options if "petrol" in opt.lower()]
            chosen_reply = petrol_opts[0] if petrol_opts else (options[0] if options else "petrol")
        elif "variant" in q_lower or field == "variant":
            vxi_opts = [opt for opt in options if "vxi" in opt.lower() or "1.2" in opt.lower()]
            chosen_reply = vxi_opts[0] if vxi_opts else (options[0] if options else "VXI")
        elif options:
            chosen_reply = options[0]
        else:
            chosen_reply = "yes"

        print(f"  Mechanic Reply: '{chosen_reply}'\n")
        q = await convo.reply(chosen_reply)
        step += 1

    print("\n✅ Conversation Completed. Sourcing outcomes obtained.")
    state = convo.state
    outcome = state.get("outcome") or {}
    all_listings = outcome.get("listings") or []

    # If outcome has vendor_outcomes, collect from both
    vendor_outcomes = outcome.get("vendor_outcomes") or []
    if not all_listings and vendor_outcomes:
        for vo in vendor_outcomes:
            all_listings.extend(vo.get("listings") or [])

    print(f"\nTotal Listings Extracted: {len(all_listings)}")

    if all_listings:
        ranked = rank_listings(all_listings, price_order="asc")
        print("\n=======================================================")
        print("📊 UNIFIED PRODUCT COMPARISON RESULTS (Relevance Ranked)")
        print("=======================================================")
        print(f"{'#':<3} | {'Relevance':<13} | {'Type':<17} | {'Price':<10} | {'Supplier':<10} | {'Title'}")
        print("-" * 95)
        for idx, item in enumerate(ranked, 1):
            rel = item.get("relevance", "N/A")
            ptype = (item.get("product_type") or "N/A").replace("_", " ")
            price_val = item.get("price")
            price_str = f"₹{price_val:,.0f}" if price_val is not None else "Unpriced"
            supp = item.get("vendor") or item.get("supplier_name") or "Auto"
            title = (item.get("title") or "")[:40]
            print(f"{idx:<3} | {rel:<13} | {ptype:<17} | {price_str:<10} | {supp:<10} | {title}")

    await close_session(thread_id)
    print("\n=======================================================")
    print("🏁 TEST COMPLETED SUCCESSFULLY")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(run_swift_clutch_test())
