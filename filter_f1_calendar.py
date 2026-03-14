import re
import urllib.request

SOURCE_URL = "https://ics.ecal.com/ecal-sub/6802beecdebd000008e3b6ef/Formula%201.ics"
OUTPUT_FILE = "f1_filtered.ics"

KEEP_ENDINGS = [
    "Race",
    "Qualifying",
    "Sprint Qualifying",
    "Sprint Shootout",
    "Sprint",
]

DROP_WORDS = [
    "Practice",
    "Training",
    "FP1",
    "FP2",
    "FP3",
    "Free Practice",
]


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


def event_should_be_kept(event_lines):
    summary = ""
    description = ""

    for line in event_lines:
        upper = line.upper()
        if upper.startswith("SUMMARY"):
            summary = normalize_text(get_prop_value(line))
        elif upper.startswith("DESCRIPTION"):
            description = normalize_text(get_prop_value(line))

    haystack = f"{summary} {description}"

    for word in DROP_WORDS:
        if word in haystack:
            return False

    # Wichtig: viele eCal-Termine enden auf " - Race", " - Qualifying" usw.
    # Daher besonders das Ende des SUMMARY prüfen.
    for ending in KEEP_ENDINGS:
        if summary.endswith(f" - {ending}") or summary.endswith(f"– {ending}") or summary.endswith(ending):
            return True

    # Fallback
    for ending in KEEP_ENDINGS:
        if ending in haystack:
            return True

    return False


def main():
    with urllib.request.urlopen(SOURCE_URL) as response:
        raw = response.read().decode("utf-8", errors="replace")

    lines = unfold_ics_lines(raw)

    calendar_props = []
    kept_events = []

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

    print(f"Kept {len(kept_events)} events.")


if __name__ == "__main__":
    main()