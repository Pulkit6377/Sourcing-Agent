"""Conversational parts search on Boodmo and AutoDukan.

    python3 run_agent.py                         # type the request and answers
    python3 run_agent.py --voice                 # speak; the agent talks back
    python3 run_agent.py --say "oil filter for a Tata Harrier" --answers 2021 "XZA plus" automatic
    python3 run_agent.py --show-browser          # watch Playwright drive the site
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import sys
import uuid

# Ensure backend directory is in sys.path
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from parts_agent.graph import Conversation, SESSIONS, close_session, open_session, save_run
from parts_agent.terminal_recorder import TerminalRecorder, compose_3in1_video, compose_split_video

DIM, BOLD, CYAN, GREEN, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[32m", "\033[0m"


def format_table(outcome: dict) -> str:
    lines = []
    vendor_outcomes = outcome.get("vendor_outcomes") or [outcome]
    vendor_names = {
        "boodmo": "Boodmo",
        "autodukan": "AutoDukan",
    }
    for vendor_outcome in vendor_outcomes:
        ls = vendor_outcome.get("listings") or []
        vendor = vendor_names.get(vendor_outcome.get("vendor"), vendor_outcome.get("vendor", "Results"))
        vehicle = vendor_outcome.get("vehicle_label") or outcome.get("vehicle_label", "")
        source_url = vendor_outcome.get("source_url")
        lines.append(f"\n{vendor}: {vehicle}" + (f"  {source_url}" if source_url else ""))
        if not ls:
            lines.append(vendor_outcome.get("message") or "No product listings returned.")
            continue
        head = f"{'#':>2}  {'match':8} {'fit':8} {'brand':11} {'title':30} {'part no':14} {'price':>9}  {'seller / stock / dispatch'}"
        lines.append(head)
        for i, listing in enumerate(ls, 1):
            offer = listing.get("best_offer") or {}
            price_value = listing.get("price")
            price = f"₹{price_value:,.0f}" if price_value is not None else "—"
            if offer:
                seller = f"{offer.get('seller')} / {offer.get('stock')} / {offer.get('dispatch')}"
            elif listing.get("available") is False:
                seller = "no seller in stock"
            elif listing.get("available") is True:
                seller = "in stock; seller not listed"
            else:
                seller = "stock not confirmed"
            lines.append(f"{i:>2}  {listing.get('match', 'exact'):8} {listing.get('fitment', 'unverified'):8} "
                         f"{(listing.get('brand') or '')[:11]:11} {(listing.get('title') or '')[:30]:30} "
                         f"{(listing.get('part_number') or '')[:14]:14} {price:>9}  {seller}")
            for note in listing.get("notes") or []:
                lines.append(f"    - {note}")
    return "\n".join(lines)


def print_table(outcome: dict) -> str:
    tbl_text = format_table(outcome)
    print(tbl_text)
    print()
    return tbl_text


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", action="store_true", help="speak and listen instead of typing")
    ap.add_argument("--show-browser", action="store_true", help="run Chromium with a visible window")
    ap.add_argument("--record-video", action="store_true", help="record browser sessions as videos in runs/videos/")
    ap.add_argument("--say", help="initial request (skips the first prompt)")
    ap.add_argument("--answers", nargs="*", default=[], help="scripted answers to follow-up questions")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    speaker = None
    if args.voice:
        from parts_agent import voice
        speaker = voice.Speaker()

    term_rec: Optional[TerminalRecorder] = None
    term_log_handler = None
    thread = str(uuid.uuid4())
    record_dir = str(Path(__file__).resolve().parent / "runs" / "videos" / thread[:8]) if args.record_video else None
    if record_dir:
        term_rec = TerminalRecorder(record_video_dir=record_dir)
        await term_rec.start()
        clean_args = [a for a in sys.argv[1:] if a not in ("--record-video",)]
        if any(a in sys.argv for a in ("--say", "--answers")):
            cmd_str = "python3 run_agent.py --show-browser -v"
        else:
            cmd_str = f"python3 run_agent.py {' '.join(clean_args)}" if clean_args else "python3 run_agent.py -v"
        await term_rec.write_prompt(cmd_str)

        class TerminalLogHandler(logging.Handler):
            def __init__(self, recorder: TerminalRecorder, loop: asyncio.AbstractEventLoop):
                super().__init__()
                self.recorder = recorder
                self.loop = loop

            def emit(self, record: logging.LogRecord):
                if not self.recorder or not self.recorder.page:
                    return
                if record.name.startswith(("parts_agent.auto_dukan", "parts_agent.boodmo", "parts_agent.llm")):
                    msg = f"INFO {record.name}: {record.getMessage()}"
                    try:
                        if self.loop.is_running():
                            asyncio.run_coroutine_threadsafe(self.recorder.write_info(msg), self.loop)
                    except Exception:
                        pass

        term_log_handler = TerminalLogHandler(term_rec, asyncio.get_running_loop())
        logging.getLogger("parts_agent").addHandler(term_log_handler)

    def say(text: str):
        print(f"{CYAN}Agent:{RESET} {text}")
        if term_rec:
            asyncio.create_task(term_rec.write_agent(text))
        if speaker:
            speaker.say(text)

    def on_progress(m: str):
        print(f"{DIM}  · {m}{RESET}")
        if term_rec:
            asyncio.create_task(term_rec.write_progress(m))

    def hear(context: str = "") -> str:
        if args.answers:
            import time
            time.sleep(1.2)
            a = args.answers.pop(0)
            print(f"{GREEN}Mechanic:{RESET} {a}")
            if term_rec:
                asyncio.create_task(term_rec.write_mechanic(a))
            return a
        if speaker:
            speaker.wait()
            for attempt in range(2):
                print(f"{DIM}  (listening…){RESET}")
                text = voice.listen(context)
                if text:
                    print(f"{GREEN}Mechanic:{RESET} {text}")
                    if term_rec:
                        asyncio.create_task(term_rec.write_mechanic(text))
                    return text
                if attempt == 0:
                    say("Sorry, I didn't hear anything.")
                    speaker.wait()
            ans = input(f"{GREEN}Mechanic (type):{RESET} ").strip()
            if term_rec and ans:
                asyncio.create_task(term_rec.write_mechanic(ans))
            return ans
        ans = input(f"{GREEN}Mechanic:{RESET} ").strip()
        if term_rec and ans:
            asyncio.create_task(term_rec.write_mechanic(ans))
        return ans

    open_session(thread, headless=not args.show_browser,
                 progress=on_progress,
                 announce=say,
                 record_video_dir=record_dir)
    convo = Conversation(thread)

    try:
        say("Which part do you need, and for which car?")
        if args.say:
            await asyncio.sleep(1.2)
            request = args.say
            print(f"{GREEN}Mechanic:{RESET} {request}")
            if term_rec:
                await term_rec.write_mechanic(request)
        else:
            request = hear()
        if not request:
            return
        q = await convo.start(request)
        while q:
            say(" ".join(x for x in (q.get("note"), q["question"]) if x))
            q = await convo.reply(hear(q["question"]))
        state = convo.state

        if state.get("outcome"):
            tbl_text = print_table(state["outcome"])
            if term_rec:
                await term_rec.write_table_text(tbl_text)
        say(state.get("summary") or "Done.")
        if speaker:
            speaker.wait()
        path = save_run(thread, state)
        print(f"{DIM}Audit record: {path}{RESET}")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
    finally:
        if term_log_handler:
            try:
                logging.getLogger("parts_agent").removeHandler(term_log_handler)
            except Exception:
                pass
        session = SESSIONS.get(thread)
        adapters = list(session.adapters.items()) if session else []
        await close_session(thread)
        term_video = None
        if term_rec:
            term_video = await term_rec.close()
        recorded = []
        dukan_video = None
        boodmo_video = None
        for name, adapter in adapters:
            vpath = getattr(adapter, "video_path", None)
            if vpath:
                recorded.append((name, vpath))
                if name == "autodukan":
                    dukan_video = vpath
                elif name == "boodmo":
                    boodmo_video = vpath
        if term_video:
            recorded.append(("terminal", term_video))
        if recorded:
            print(f"\n{BOLD}Recorded raw videos:{RESET}")
            for name, vp in recorded:
                print(f"  {CYAN}{name}:{RESET} {vp}")

        # Generate composited side-by-side and 3-in-1 videos
        if term_video and dukan_video and boodmo_video and record_dir:
            master_mp4 = str(Path(record_dir) / "master_search_demo_3in1.mp4")
            print(f"\n{BOLD}Compositing Master 3-in-1 Demo Video (Terminal + AutoDukan + Boodmo)...{RESET}")
            if compose_3in1_video(term_video, dukan_video, boodmo_video, master_mp4):
                print(f"  {GREEN}✓ Master 3-in-1 Video:{RESET} {master_mp4}")

            dukan_split = str(Path(record_dir) / "terminal_and_autodukan_split.mp4")
            if compose_split_video(term_video, dukan_video, dukan_split, "AutoDukan"):
                print(f"  {GREEN}✓ Terminal + AutoDukan Video:{RESET} {dukan_split}")

            boodmo_split = str(Path(record_dir) / "terminal_and_boodmo_split.mp4")
            if compose_split_video(term_video, boodmo_video, boodmo_split, "Boodmo"):
                print(f"  {GREEN}✓ Terminal + Boodmo Video:{RESET} {boodmo_split}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
