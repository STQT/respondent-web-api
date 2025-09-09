import re
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.surveys.models import Survey, Question, Choice  # adjust import to your app label
# pip install python-docx
from docx import Document

UZ_CYR_LETTERS = {
    # Cyrillic letters used in options -> Latin index
    "А": "A", "а": "A",
    "Б": "B", "б": "B",
    "В": "C", "в": "C",
    "Г": "D", "г": "D",
    "Д": "E", "д": "E",
}

OPTION_PREFIX_PAT = re.compile(
    r"^\s*([A-Da-dА-Га-г])[\.\)\:]?\s+"  # A) A. А) А. etc
)

QUESTION_NUM_PREFIX = re.compile(r"^\s*(\d{1,3})\s*[\)\.\:]\s*(.+)$")

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def is_question_line(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    # numbered "1) ..." / "1. ..." / "1: ...", or ends with ?
    if QUESTION_NUM_PREFIX.match(t):
        return True
    return t.endswith("?") and len(t) > 6

def normalize_option_key(ch: str) -> str:
    ch = ch.strip()
    if ch in UZ_CYR_LETTERS:
        return UZ_CYR_LETTERS[ch]
    return ch.upper()

def extract_key_table(lines):
    """
    Extract answer key dict: {question_number(int): 'A'/'B'/...}
    Looks for a section containing the word 'Калит' or 'Key'
    and pairs like '1  Г' or '1) Г' or in columns.
    """
    key_started = False
    key_map = {}
    buf = []

    for line in lines:
        t = line.strip()
        if not key_started:
            if re.search(r"\b(Калит|Ключ|Key)\b", t, re.IGNORECASE):
                key_started = True
            continue
        buf.append(t)

    # Join and split by any whitespace/newline; also capture simple pairs in lines
    # Accept formats like "1  Г" or "1 Г" or "1) Г"
    pair_pat = re.compile(r"(\d{1,3})\s*[\)\.:]?\s*([A-Da-dА-Га-г])")
    for t in buf:
        for m in pair_pat.finditer(t):
            qn = int(m.group(1))
            key = normalize_option_key(m.group(2))
            key_map[qn] = key
    return key_map

def parse_docx(docx_path: Path):
    """
    Returns list of dicts:
    [{'qnum': optional int, 'text': str, 'choices': [{'text': str, 'ok': bool}], 'multi': bool}]
    Supports inline ✅ markers and/or a trailing Key table.
    """
    doc = Document(str(docx_path))
    lines = []
    for p in doc.paragraphs:
        txt = p.text
        if txt and txt.strip():
            lines.append(txt)

    # Try to capture a key table if present
    key_map = extract_key_table(lines)

    # State machine: accumulate a question until next question starts
    items = []
    cur = None
    q_order_counter = 0

    def commit_current():
        nonlocal cur, items
        if cur and clean_text(cur.get("text", "")):
            # If no explicit correctness and have key_map + qnum, mark by key
            opts = cur.get("choices", [])
            if opts:
                # If no any ok marked:
                if not any(o.get("ok") for o in opts) and cur.get("qnum") and key_map.get(cur["qnum"]):
                    key = key_map[cur["qnum"]]
                    # Find option by A/B/C/D order
                    # We assume options were appended in order A..Z
                    idx_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
                    if key in idx_map and idx_map[key] < len(opts):
                        opts[idx_map[key]]["ok"] = True
            # detect multi if >=2 ok
            ok_count = sum(1 for o in cur.get("choices", []) if o.get("ok"))
            cur["multi"] = ok_count > 1
            items.append(cur)
        cur = None

    for raw in lines:
        line = clean_text(raw)
        if not line:
            continue

        # Skip entire key block lines from becoming questions
        if re.search(r"\b(Калит|Ключ|Key)\b", line, re.IGNORECASE):
            # Commit current and break further parsing of Q/A
            commit_current()
            break

        # New question?
        qnum = None
        qtxt = None
        m = QUESTION_NUM_PREFIX.match(line)
        if m:
            qnum = int(m.group(1))
            qtxt = clean_text(m.group(2))

        if is_question_line(line) or qnum is not None:
            # start new question
            commit_current()
            q_order_counter += 1
            cur = {
                "qnum": qnum,
                "text": qtxt if qtxt else line,
                "choices": []
            }
            continue

        # Option?
        om = OPTION_PREFIX_PAT.match(line)
        if om and cur is not None:
            # Strip prefix
            key = normalize_option_key(om.group(1))
            body = clean_text(line[om.end():])
            ok = "✅" in line
            # Remove ✅ from text
            body = body.replace("✅", "").strip()
            cur["choices"].append({"text": body, "ok": ok})
            continue

        # Bulleted option without A/B etc, but with ✅
        if cur is not None and ("✅" in line or re.match(r"^[•\-–]\s+", line)):
            text = line.replace("✅", "").lstrip("•-–").strip()
            ok = "✅" in line
            cur["choices"].append({"text": text, "ok": ok})
            continue

        # Fallback: if we have a current question but line is continuation, append to question text
        if cur is not None and not OPTION_PREFIX_PAT.match(line):
            # join long question text
            cur["text"] = (cur["text"] + " " + line).strip()

    # commit last
    commit_current()
    return items


class Command(BaseCommand):
    help = "Import questions/choices from DOCX files into a Survey"

    def add_arguments(self, parser):
        parser.add_argument("--survey-id", type=int, default=1)
        parser.add_argument("--files", nargs="+", required=True, help="Paths to .docx files")
        parser.add_argument("--language", choices=["uz", "uz-cyrl", "ru"], default="uz")
        parser.add_argument("--points", type=int, default=1)
        parser.add_argument("--reset", action="store_true", help="Delete existing questions before import")
        parser.add_argument("--only-single", action="store_true",
                            help="Force all questions to 'single' even if multiple ✅ found")

    def handle(self, *args, **opts):
        survey_id = opts["survey_id"]
        lang = opts["language"]
        points = opts["points"]
        paths = [Path(p) for p in opts["files"]]

        try:
            survey = Survey.objects.get(pk=survey_id)
        except Survey.DoesNotExist:
            raise CommandError(f"Survey id={survey_id} not found")

        for p in paths:
            if not p.exists():
                raise CommandError(f"File not found: {p}")
            if p.suffix.lower() != ".docx":
                raise CommandError(f"Unsupported file type (need .docx): {p}")

        with transaction.atomic():
            if opts["reset"]:
                # careful with unique_together (survey, order)
                survey.questions.all().delete()
                self.stdout.write(self.style.WARNING("Existing questions deleted."))

            # figure next order start
            next_order = (survey.questions.aggregate_max("order") or 0) if hasattr(survey.questions, "aggregate_max") else 0
            if not next_order:
                try:
                    next_order = survey.questions.order_by("-order").first().order + 1
                except Exception:
                    next_order = 1

            total_q = 0
            total_c = 0

            for p in paths:
                items = parse_docx(p)
                self.stdout.write(f"Parsed {len(items)} questions from {p.name}")

                for idx, it in enumerate(items, start=1):
                    qtext = it["text"]
                    choices = it.get("choices", [])

                    if not qtext or not choices:
                        # Skip open questions for now (no options)
                        continue

                    qtype = "multiple" if (not opts["only-single"] and sum(1 for c in choices if c.get("ok")) > 1) else "single"

                    q = Question(
                        survey=survey,
                        question_type=qtype,
                        points=points,
                        order=next_order,
                        is_active=True,
                    )
                    # set language-specific text
                    if lang == "uz":
                        q.text_uz = qtext
                        q.text_uz_cyrl = ""
                        q.text_ru = ""
                    elif lang == "uz-cyrl":
                        q.text_uz_cyrl = qtext
                        q.text_uz = ""
                        q.text_ru = ""
                    else:
                        q.text_ru = qtext
                        q.text_uz = ""
                        q.text_uz_cyrl = ""

                    q.save()
                    total_q += 1

                    # create choices
                    for n, ch in enumerate(choices, start=1):
                        c = Choice(
                            question=q,
                            is_correct=bool(ch.get("ok")),
                            order=n
                        )
                        if lang == "uz":
                            c.text_uz = ch["text"]
                            c.text_uz_cyrl = ""
                            c.text_ru = ""
                        elif lang == "uz-cyrl":
                            c.text_uz_cyrl = ch["text"]
                            c.text_uz = ""
                            c.text_ru = ""
                        else:
                            c.text_ru = ch["text"]
                            c.text_uz = ""
                            c.text_uz_cyrl = ""
                        c.save()
                        total_c += 1

                    next_order += 1

            self.stdout.write(self.style.SUCCESS(
                f"Imported {total_q} questions and {total_c} choices into Survey(id={survey_id})."
            ))
