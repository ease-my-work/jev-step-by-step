"""Check that your keys and models work: one JEV call and one Gemini call, with timings.

python scripts/check_setup.py
python scripts/check_setup.py --runs 3     # repeat to see warm-connection timings
"""

import argparse
import sys

from google.genai import types
from typesafe_sdk import Choice, Noul, TypeSafeError

import kit
from kit import settings

QUERY = "My order debited amount 2 time. I want immediate help."
TEAMS = ["billing", "shipping", "technical", "account", "other"]


def check_jev(runs: int) -> bool:
    try:
        jev = kit.jev_client()
        for _ in range(runs):
            with kit.recording() as calls:
                response = jev.system_one(
                    state=QUERY,
                    questions={
                        "team": Choice(instructions="Which team should handle this?", criteria=dict.fromkeys(TEAMS)),
                        "urgent": Noul(instructions="The customer needs help today."),
                    },
                )
            team, urgent = response.answers["team"], response.answers["urgent"]
            call = calls[0]
            print(
                f"  ✔ team={team.choice} (confidence {team.confidence:.2f})  urgent={urgent.noul:.2f}"
                f"  ⏱ {call.ms:,.0f} ms  [{call.model}, {call.input_tokens} in / {call.output_tokens} out]"
            )
        return True
    except (kit.SetupError, TypeSafeError) as error:
        print(f"  ✘ {type(error).__name__}: {error}")
        return False


def check_gemini(runs: int) -> bool:
    try:
        gemini = kit.gemini_client()
        schema = {"type": "object", "properties": {"team": {"type": "string", "enum": TEAMS}}, "required": ["team"]}
        for _ in range(runs):
            with kit.recording() as calls:
                response = gemini.models.generate_content(
                    model=kit.GEMINI_MODEL,
                    contents=f"Which team should handle this customer message?\n\n{QUERY}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        thinking_config=kit.GEMINI_THINKING,
                    ),
                )
            call = calls[0]
            waited = f"  (waited {call.waited_ms / 1000:.1f} s for rate limit)" if call.waited_ms > 50 else ""
            print(
                f"  ✔ {response.parsed}  ⏱ {call.ms:,.0f} ms  "
                f"[{call.model}, {call.input_tokens} in / {call.output_tokens} out"
                f" / {call.thinking_tokens or 0} thinking]{waited}"
            )
        return True
    except Exception as error:  # Gemini SDK raises several unrelated types; show any of them plainly.
        print(f"  ✘ {type(error).__name__}: {str(error)[:300]}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=1, help="calls per side (default 1)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ✔/✘ on older Windows consoles

    print("Settings (from .env)")
    print(f"  JEV model      {settings.JEV_MODEL}")
    print(f"  JEV base URL   {settings.env('TYPESAFE_BASE_URL', 'https://api.typesafe.ai (default)')}")
    print(f"  JEV key        {'set' if settings.env('TYPESAFE_API_KEY') else 'MISSING'}")
    print(f"  Gemini model   {settings.GEMINI_MODEL}  (thinking: {settings.GEMINI_THINKING_LEVEL})")
    print(f"  Gemini key     {'set' if settings.env('GEMINI_API_KEY') else 'MISSING'}")
    if "latest" in settings.JEV_MODEL:
        print(f"  ⚠ JEV_MODEL={settings.JEV_MODEL} floats to new versions. Pin it, e.g. jev-1.13 / typesafe/jev-1.13.")

    print(f'\nQuery: "{QUERY}"\n\nJEV')
    jev_ok = check_jev(args.runs)
    print("\nLLM-only (Gemini)")
    gemini_ok = check_gemini(args.runs)

    print(
        "\nAll good — you're ready for step 01." if jev_ok and gemini_ok else "\nFix the ✘ lines above and run again."
    )
    return 0 if jev_ok and gemini_ok else 1


if __name__ == "__main__":
    sys.exit(main())
