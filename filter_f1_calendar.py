import re
import urllib.request

SOURCE_URL = "https://ics.ecal.com/ecal-sub/6802beecdebd000008e3b6ef/Formula%201.ics"
OUTPUT_FILE = "f1_filtered.ics"

ALLOWED_TYPES = {
    "Race",
    "Qualifying",
    "Sprint",
    "Sprint Qualifying",
    "Sprint Shootout",
}

BLOCKED_WORDS = {
    "Practice",
    "Training",
    "FP1",
    "FP2",
    "FP3",
    "Free Practice",
}


def unfold_ics_lines(text: str):
    lines = text.splitlines()
    out = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def fold_ics_line(line: str, limit: int = 75):
    if len(line) <= limit:
        return [line]
    parts = [line[:limit]]
    rest = line[limit:]
    while rest:
        parts.append(" " + rest[: limit - 1])
        rest = rest[limit - 1 :]
    return parts


def get_prop_value(line: str) -> str:
    return line.split(":", 1)[1] if ":" in line else ""


def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def parse_event_type(summary: str) -> str:
    summary = normalize_text(summary)

    # nimm den Teil nach dem letzten Trenner
    for sep in [" - ", " – ", " — ", ": "]:
        if sep in summary:
            return summary.rsplit(sep, 1)[-1].strip()

    return summary.strip()


def event_should_be_kept(event_lines):
    summary = ""
    description = ""

    for line in event_lines:
        upper = line.upper()
        if upper.startswith("SUMMARY"):
            summary = get_prop_value(line)
        elif upper.startswith("DESCRIPTION"):
            description = get_prop_value(line)

    text = normalize_text(summary + " " + description)

    for word in BLOCKED_WORDS:
        if word in text:
            return False

    event_type = parse_event_type(summary)

    if event_type in ALLOWED_TYPES:
        return True

    # Fallback: falls der Event-Typ nicht sauber getrennt ist
    for allowed in ALLOWED_TYPES:
        if summary.lower().endswith(allowed):
            return True

    return False


def main():
    with urllib.request.urlopen(SOURCE_URL) as response:
        raw = response.read().decode("utf-8", errors="replace")

    lines = unfold_ics_lines(raw)

    calendar_props = []
    kept_events = []
    found_summaries = []

    in_event = False
    event_lines = []

    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            event_lines = [line]
            continue

        if line == "END:VEVENT":
            event_lines.append(line)
            in_event = False

            for l in event_lines:
                if l.upper().startswith("SUMMARY"):
                    found_summaries.append(get_prop_value(l))
                    break

            if event_should_be_kept(event_lines):
                kept_events.append(event_lines)

            event_lines = []
            continue

        if in_event:
            event_lines.append(line)
        else:
            if line not in ("BEGIN:VCALENDAR", "END:VCALENDAR"):
                calendar_props.append(line)

    output_lines = ["BEGIN:VCALENDAR"]

    saw_name = False
    for line in calendar_props:
        if line.upper().startswith("X-WR-CALNAME"):
            output_lines.append("X-WR-CALNAME:Formula 1 (Filtered)")
            saw_name = True
        else:
            output_lines.append(line)

    if not saw_name:
        output_lines.append("X-WR-CALNAME:Formula 1 (Filtered)")

    for event in kept_events:
        output_lines.extend(event)

    output_lines.append("END:VCALENDAR")

    folded = []
    for line in output_lines:
        folded.extend(fold_ics_line(line))

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(folded) + "\r\n")

    print(f"Found {len(found_summaries)} total events")
    print(f"Kept {len(kept_events)} events")
    print("--- First 20 summaries from source ---")
    for s in found_summaries[:20]:
        print(s)
    print("--- First 20 kept summaries ---")
    for event in kept_events[:20]:
        for line in event:
            if line.upper().startswith("SUMMARY"):
                print(get_prop_value(line))
                break


if __name__ == "__main__":
    main()