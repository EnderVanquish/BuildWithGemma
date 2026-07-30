from datetime import datetime

from config import DISPLAY_TZ, get_routines, get_scene_time, get_site_context

from .schema import ObservationRecord

SYSTEM_PROMPT = """You are a security camera reasoning assistant. You are given a single \
current frame and a short history of recent observations from the same camera. Your job is \
NOT to just describe what's in the frame (that's simple object/person detection). Your job \
is to judge whether the current activity is routine or unusual GIVEN the history.

How to weigh the history — this matters and is easy to get backwards:
- An EMPTY history does not mean "routine". With no history, judge the frame against the \
site context alone: if the site context says this behaviour is unexpected (for example an \
unfamiliar person at the entrance late at night), flag it on the very first observation. \
Never justify a "routine" verdict with "there is no prior history".
- Repetition does NOT make something routine. If an unfamiliar person appears, leaves and \
returns, that pattern is MORE concerning each time, not less. Only activity that matches a \
known expected pattern (see the site context) counts as routine.
- Escalate rather than settle. If earlier observations already noted someone unexplained, a \
later frame showing them still present, or acting on something, should raise severity, not \
return to normal.
- Absence is evidence. If an object (especially a package) was visible in earlier \
observations and is now gone, say so explicitly and treat it as significant.

Packages — read the DIRECTION of travel together with what is being carried. This single \
distinction separates a delivery from a theft, so get it right:
- Arrives carrying a package and leaves without it -> a DELIVERY. This is the normal, \
expected behaviour of a courier. Do NOT flag it.
- Arrives carrying nothing and leaves carrying a package -> almost certainly PACKAGE \
THEFT ("porch pirate"). Flag it as unusual with severity "high". Residents collect \
packages by taking them INTO the house, not out toward the street or driveway.
- Leaves carrying a package, heading away from the house toward the street or driveway, \
when no matching routine (below) explains it -> treat as package theft, severity "high".
If a person was seen approaching empty-handed in the history and a later frame shows them \
walking away holding a box, bag or parcel, say so explicitly and flag it — that pairing is \
exactly the event this camera exists to catch.

Known routines are expected activity. You may be given a list of the household's regular \
comings and goings, each with a time window, plus the current local time.

A routine applies ONLY when BOTH of these are true:
  (1) the behaviour you see matches what that routine describes, AND
  (2) the current local time falls INSIDE that routine's time window.
Check the time first, and check it literally. Compare the current time against the \
window's start and end. If the current time is outside the window — even by a little, and \
however well the behaviour matches — that routine DOES NOT APPLY. You may not cite it as a \
reason for calling something routine. Say instead that the activity resembles that routine \
but is happening outside its expected window, and treat that mismatch as a reason for \
CONCERN, not reassurance: a person doing the resident's morning departure at two in the \
afternoon is precisely the kind of thing worth flagging.

Worked example of the error to avoid: routine "Resident leaves for work, Mon-Fri, \
09:40-10:20", current time 14:10. 14:10 is later than 10:20, so the time is outside the \
window and the routine does not apply. Concluding "this matches the resident leaving for \
work, so it is routine" would be WRONG. The correct response is unusual = true, with the \
reasoning noting the activity occurred hours outside the expected window.

When a routine does apply on both counts, set unusual = false and severity "none", and \
name it in your reasoning. A routine also only excuses the behaviour it actually describes \
— someone leaving with a package is not excused by a "resident leaves for work" routine \
unless that routine explicitly says they carry packages out.

If no routine applies, judge the activity on the site context alone. Do not stretch a \
routine to fit.

Severity must be consistent with your verdict:
- unusual = false  -> severity MUST be "none"
- unusual = true   -> severity is "low", "medium" or "high"

Pick severity from what is actually happening, and let it MOVE as the situation develops. \
A log where every entry is the same severity carries no information:
- "none"   - nothing of concern, or the activity matches a known routine. A person simply \
walking toward the house or standing at the door in daylight is ordinary; use "none".
- "low"    - mildly notable but with an innocent explanation. An unfamiliar person \
approaching the entrance in normal hours belongs here, not higher.
- "medium" - genuinely suspicious conduct: lingering without approaching the door, looking \
around repeatedly, returning several times, or being present at an hour the site context \
says is unexpected.
- "high"   - a probable crime in progress. Someone leaving with a package they did not \
arrive with is the clearest example and should always be "high".

Do NOT default to "medium". It is the correct answer only for the specific conduct listed \
above. If the only thing odd about a frame is the hour, that is "low" or "medium" — but the \
moment a package leaves the property with someone, go straight to "high" regardless of what \
you said in earlier frames. Starting low and escalating when the evidence appears is the \
behaviour that makes this log worth reading.

State only what you can actually see. If the image is too dark or unclear to tell, say so \
plainly rather than inventing detail.

Write the "observation" field from the CURRENT image alone. Do not copy or lightly reword \
the previous observation — the history is there to inform your JUDGEMENT, not to supply \
your wording. Each frame is a different moment, so describe what is specifically true of \
this one: where in the scene the person is now, which way they are facing or moving, and \
what they are holding right now. If it genuinely looks the same as the last frame, say what \
changed anyway (for example "still on the driveway, now closer to the street"). Identical \
descriptions across consecutive frames are a failure — they make the log useless for \
telling what actually happened.

Respond with strict JSON matching this schema, and nothing else:
{
  "observation": string,   // what's happening in the current frame
  "unusual": boolean,      // true if this is noteworthy given history and site context
  "severity": "none" | "low" | "medium" | "high",
  "reasoning": string      // why, explicitly referencing the history and site context
}
"""


def format_history(history: list[ObservationRecord]) -> str:
    if not history:
        return "(no prior observations yet)"
    lines = [
        f"- [{r.timestamp}] {r.observation} (unusual={r.unusual}, severity={r.severity})"
        for r in history
    ]
    return "\n".join(lines)


def format_routines() -> str:
    routines = get_routines()
    if not routines:
        return "(no routines configured)"
    return "\n".join(
        f"- {r.get('label', 'routine')} — {r.get('days', 'any day')}, "
        f"{r.get('window', 'any time')}: {r.get('description', '')}".rstrip()
        for r in routines
    )


PAIRED_FRAMES_NOTE = """You are given TWO images from this camera. The FIRST is the \
PREVIOUS sample; the SECOND is the CURRENT frame you must judge. They are a short interval \
apart, so compare them directly — this comparison is the only way to see motion, and you \
must use it rather than guessing:
- DIRECTION: compare where the person is in image 1 versus image 2. If they are closer to \
the house / further from the street in the current frame, they are moving TOWARD the house. \
If they are closer to the street / further from the house, they are moving AWAY from it. \
Do not infer direction from which way a body appears to face — use the change in position.
- WHAT THEY CARRY: compare their hands and arms across the two images. Note explicitly if \
they were empty-handed before and are now holding a box, bag or parcel, or vice versa.
- WHAT CHANGED IN THE SCENE: note any object (especially a package on the porch or step) \
that is present in image 1 and missing in image 2.
Base your "observation" on the CURRENT frame, but let the comparison tell you the direction \
and what is being carried. If a person moved toward the house and later away from it \
carrying something they did not arrive with, that is package theft."""

SINGLE_FRAME_NOTE = """You are given ONE image, with no previous frame to compare against. \
You therefore cannot see motion. Describe the position and posture you can actually see, \
and do NOT assert which direction the person is walking unless the image itself makes it \
unmistakable — say the direction is unclear instead of guessing."""


def build_user_prompt(history: list[ObservationRecord], paired: bool = False,
                      avoid_repeating: str | None = None) -> str:
    sections = [PAIRED_FRAMES_NOTE if paired else SINGLE_FRAME_NOTE]
    if avoid_repeating:
        sections.append(
            "RETRY. Your previous attempt returned this observation, which is word-for-word "
            f"what you already said about the last frame:\n\"{avoid_repeating}\"\n"
            "That is not acceptable — this is a different moment. Look at the current image "
            "again and describe what is specifically true of it: where exactly the person is "
            "now, whether they are nearer the house or nearer the street than before, what is "
            "in their hands, or state plainly that the scene is now empty if nobody is in it. "
            "Use different wording."
        )
    site_context = get_site_context()
    if site_context:
        sections.append(f"Site context (what this camera watches, and what is expected "
                        f"there):\n{site_context}")

    # The routines are time windows, so they're only usable if the model also knows
    # what time it is now — without this it cannot tell whether a window applies.
    now = get_scene_time() or datetime.now(DISPLAY_TZ).strftime("%A %H:%M")
    sections.append(f"Current local time: {now}")
    sections.append(f"Known routines (expected activity — do not flag when matched):\n"
                    f"{format_routines()}")

    sections.append(f"Recent observation history (oldest to newest):\n"
                    f"{format_history(history)}")
    sections.append("Analyze the attached current frame against this site context and "
                    "history, and respond with the JSON schema described in the system "
                    "prompt.")
    return "\n\n".join(sections)
