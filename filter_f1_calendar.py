import urllib.request
from datetime import datetime, timezone

SOURCE_URL = "https://ics.ecal.com/ecal-sub/6802beecdebd000008e3b6ef/Formula%201.ics"
OUTPUT_FILE = "f1_filtered.ics"

# Nur diese Event-Typen behalten
KEEP_KEYWORDS = [
    "Qualifying",
    "Race",
    "Sprint Qualification",
    "Sprint Race",   # falls der Feed das so nennt
    "Sprint"
]

# Diese explizit verwerfen
DROP_KEYWORDS = [
    "Practice",
    "Training",
    "fp1",
    "fp2",
    "fp3",
    "free practice"
]


def unfold_ics_lines(text: str):
    lines = text.splitlines()
    unfolded = []
    for line in lines:
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def fold_ics_line(line: str, limit: int = 75):
    if len(line) <= limit:
        return [line]
    parts = [line[:limit]]
    rest = line[limit:]
    while rest:
        parts.append(" " + rest[:limit - 1])
        rest = rest[limit - 1:]
    return parts


def event_should_be_kept(event_lines):
    summary = ""
    description = ""

    for line in event_lines:
        upper = line.upper()
        if upper.startswith("SUMMARY"):
            summary = line.split(":", 1)[1].strip().lower() if ":" in line else ""
        elif upper.startswith("DESCRIPTION"):
            description = line.split(":", 1)[1].strip().lower() if ":" in line else ""

    text = f"{summary} {description}".lower()

    # Erst Ausschlussregeln
    for kw in DROP_KEYWORDS:
        if kw in text:
            return False

    # Dann Einschlussregeln
    for kw in KEEP_KEYWORDS:
        if kw in text:
            return True

    return False


def main():
    with urllib.request.urlopen(SOURCE_URL) as response:
        raw = response.read().decode("utf-8", errors="replace")

    lines = unfold_ics_lines(raw)

    calendar_header = []
    calendar_footer = []
    kept_events = []

    inside_event = False
    current_event = []

    for line in lines:
        if line == "BEGIN:VEVENT":
            inside_event = True
            current_event = [line]
        elif line == "END:VEVENT":
            current_event.append(line)
            inside_event = False
            if event_should_be_kept(current_event):
                kept_events.append(current_event)
            current_event = []
        else:
            if inside_event:
                current_event.append(line)
            else:
                if not kept_events and line != "END:VCALENDAR":
                    calendar_header.append(line)
                else:
                    calendar_footer.append(line)

    # Falls Header/Footer nicht sauber erkannt wurden
    if not calendar_header:
        calendar_header = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Custom F1 Filter//EN",
            "CALSCALE:GREGORIAN",
            "X-WR-CALNAME:Formula 1 (Filtered)"
        ]

    if not any(line == "END:VCALENDAR" for line in calendar_footer):
        calendar_footer = ["END:VCALENDAR"]

    output_lines = []

    # Header
    for line in calendar_header:
        if line.startswith("X-WR-CALNAME"):
            line = "X-WR-CALNAME:Formula 1 (Filtered)"
        for folded in fold_ics_line(line):
            output_lines.append(folded)

    # Zusätzlicher Zeitstempel
    output_lines.append(f"X-WR-CALDESC:Automatically filtered at {datetime.now(timezone.utc).isoformat()}")

    # Events
    for event in kept_events:
        for line in event:
            for folded in fold_ics_line(line):
                output_lines.append(folded)

    # Footer
    footer_has_end = False
    for line in calendar_footer:
        if line == "END:VCALENDAR":
            footer_has_end = True
        for folded in fold_ics_line(line):
            output_lines.append(folded)

    if not footer_has_end:
        output_lines.append("END:VCALENDAR")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\r\n".join(output_lines) + "\r\n")

    print(f"Done. Kept {len(kept_events)} events.")


if __name__ == "__main__":
    main()