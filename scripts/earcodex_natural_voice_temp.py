#!/usr/bin/env python3
"""Generate a naturally paced South African-English female narration master."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects, silence

TOTAL_MS = 173_934
SAMPLE_RATE = 24_000
OUT_DIR = Path("temp_output")
CLIP_DIR = OUT_DIR / "clips"


@dataclass(frozen=True)
class Phrase:
    text: str
    pause_ms: int
    rate: str = "-3%"
    pitch: str = "+0Hz"
    volume: str = "+0%"


@dataclass(frozen=True)
class SegmentPlan:
    start_ms: int
    end_ms: int
    lead_ms: int
    tail_ms: int
    phrases: tuple[Phrase, ...]


SEGMENTS: tuple[SegmentPlan, ...] = (
    SegmentPlan(
        0,
        12_000,
        520,
        320,
        (
            Phrase("Welcome to Ear Code X.", 420, "-7%", "+1Hz"),
            Phrase(
                "It's a South African insurance-operations prototype, built around verified data, controlled workflows, and a clear audit trail.",
                520,
                "-4%",
                "+0Hz",
            ),
            Phrase("Let's take a closer look.", 0, "-4%", "+2Hz"),
        ),
    ),
    SegmentPlan(
        12_000,
        30_000,
        260,
        420,
        (
            Phrase(
                "This browser-based demonstration shows where the prototype stands today,",
                210,
                "-4%",
                "+0Hz",
            ),
            Phrase(
                "and how it moves towards a controlled insurer pilot.",
                460,
                "-3%",
                "+1Hz",
            ),
            Phrase(
                "In one operating layer, Ear Code X brings together onboarding, claims, documents, reconciliation, reporting, audit trails, and integration-ready workflows.",
                0,
                "-2%",
                "+0Hz",
            ),
        ),
    ),
    SegmentPlan(
        30_000,
        54_000,
        250,
        540,
        (
            Phrase("Access is role-based.", 380, "-6%", "+0Hz"),
            Phrase(
                "So, whether you're an insurer, an administrator, a broker, a field agent, a group scheme, or a policyholder, you enter through a dedicated portal.",
                500,
                "-3%",
                "+1Hz",
            ),
            Phrase(
                "Multi-factor authentication is available, and each person is guided to the workspace that matches their role.",
                0,
                "-3%",
                "+0Hz",
            ),
        ),
    ),
    SegmentPlan(
        54_000,
        70_000,
        260,
        500,
        (
            Phrase(
                "Once inside, teams see only the functions they need for their responsibilities.",
                420,
                "-4%",
                "+0Hz",
            ),
            Phrase(
                "Here, the claims workspace gives us the clearest end-to-end view of how the current prototype works.",
                0,
                "-3%",
                "+1Hz",
            ),
        ),
    ),
    SegmentPlan(
        70_000,
        113_000,
        220,
        720,
        (
            Phrase(
                "Each claim displays its reference, value, processing stage, and a live service-level indicator.",
                430,
                "-3%",
                "+0Hz",
            ),
            Phrase(
                "A handler can move the case from submitted documents, through assessor review, to approval, and then issue a payment instruction.",
                520,
                "-2%",
                "+0Hz",
            ),
            Phrase("Most importantly, every sensitive decision remains visible.", 420, "-6%", "+1Hz"),
            Phrase(
                "The aim is accountable automation, with people still in control; not unsupervised decision-making.",
                520,
                "-4%",
                "-1Hz",
            ),
            Phrase(
                "A reviewer can see what changed, who acted, and where the case sits against its service target.",
                380,
                "-3%",
                "+0Hz",
            ),
            Phrase(
                "Nothing important disappears into a black box, and the operational evidence remains available for service-level review and audit reporting.",
                0,
                "-4%",
                "-1Hz",
            ),
        ),
    ),
    SegmentPlan(
        113_000,
        135_000,
        180,
        420,
        (
            Phrase(
                "Once a claim is approved, Ear Code X generates a structured payment-instruction advice.",
                350,
                "-2%",
                "+0Hz",
            ),
            Phrase(
                "It records the claim and policy references, the authorised beneficiary, masked banking details, and the approved settlement amount.",
                390,
                "+0%",
                "+0Hz",
            ),
            Phrase("It also makes one point clear.", 300, "-5%", "+1Hz"),
            Phrase(
                "Ear Code X creates the instruction; the authorised insurer or binder partner still executes the payment.",
                0,
                "+0%",
                "-1Hz",
            ),
        ),
    ),
    SegmentPlan(
        135_000,
        160_000,
        190,
        400,
        (
            Phrase("The prototype also shows structured digital onboarding.", 340, "-4%", "+1Hz"),
            Phrase(
                "A field agent selects the broker, plan and cover; records the member, beneficiary and banking details; accepts the mandate; and captures a digital signature.",
                440,
                "-1%",
                "+0Hz",
            ),
            Phrase(
                "The result is a traceable application reference, not another unstructured email attachment.",
                430,
                "-4%",
                "+0Hz",
            ),
            Phrase(
                "Ear Code X is a completed prototype in active development, and it is not yet in full production.",
                0,
                "-2%",
                "-1Hz",
            ),
        ),
    ),
    SegmentPlan(
        160_000,
        TOTAL_MS,
        140,
        150,
        (
            Phrase(
                "Next comes product hardening, POPIA readiness, and a controlled insurer pilot using between one hundred and five hundred anonymised cases, measuring speed, accuracy, reconciliation and audit evidence.",
                260,
                "+3%",
                "+0Hz",
            ),
            Phrase(
                "The goal: a secure, integration-capable platform, validated by an insurance partner.",
                220,
                "+3%",
                "+1Hz",
            ),
            Phrase(
                "Ear Code X: trusted data, faster claims, and scalable insurance operations.",
                0,
                "+1%",
                "-1Hz",
            ),
        ),
    ),
)


def trim_clip(clip: AudioSegment) -> AudioSegment:
    """Remove excessive machine silence while keeping natural breath room."""
    if len(clip) < 200:
        return clip
    threshold = max(-48.0, clip.dBFS - 22.0)
    lead = silence.detect_leading_silence(clip, silence_threshold=threshold, chunk_size=10)
    reverse = clip.reverse()
    trail = silence.detect_leading_silence(reverse, silence_threshold=threshold, chunk_size=10)
    start = max(0, lead - 35)
    end = min(len(clip), len(clip) - trail + 55)
    if end <= start:
        return clip
    return clip[start:end]


def ensure_format(clip: AudioSegment) -> AudioSegment:
    return clip.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)


def tempo_fit(clip: AudioSegment, max_ms: int, stem: str) -> AudioSegment:
    """Speed up only when necessary, preserving pitch through ffmpeg atempo."""
    if len(clip) <= max_ms:
        return clip
    factor = len(clip) / max_ms
    if factor > 1.32:
        raise RuntimeError(
            f"Segment {stem} requires excessive time compression: {len(clip)}ms -> {max_ms}ms ({factor:.3f}x)"
        )
    src = CLIP_DIR / f"{stem}_before_fit.wav"
    dst = CLIP_DIR / f"{stem}_fitted.wav"
    clip.export(src, format="wav")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-filter:a",
            f"atempo={factor:.6f}",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(dst),
        ],
        check=True,
    )
    return ensure_format(AudioSegment.from_file(dst))


async def choose_voice() -> str:
    voices = await edge_tts.list_voices()
    names = {item.get("ShortName") for item in voices}
    preferred = (
        "en-ZA-LeahNeural",
        "en-GB-SoniaNeural",
        "en-GB-LibbyNeural",
    )
    for name in preferred:
        if name in names:
            return name
    for item in voices:
        if item.get("Locale") == "en-ZA" and item.get("Gender") == "Female":
            return str(item["ShortName"])
    for item in voices:
        if item.get("Locale", "").startswith("en-") and item.get("Gender") == "Female":
            return str(item["ShortName"])
    raise RuntimeError("No suitable English female neural voice was returned by the service.")


async def synthesise_phrase(voice: str, phrase: Phrase, path: Path) -> AudioSegment:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(
                phrase.text,
                voice,
                rate=phrase.rate,
                pitch=phrase.pitch,
                volume=phrase.volume,
                receive_timeout=90,
            )
            await communicate.save(str(path))
            clip = ensure_format(AudioSegment.from_file(path))
            clip = trim_clip(clip)
            if clip.dBFS != float("-inf"):
                target_dbfs = -19.0
                clip = clip.apply_gain(target_dbfs - clip.dBFS)
            return clip.fade_in(8).fade_out(18)
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1.5 * attempt)
    raise RuntimeError(f"TTS failed after three attempts for: {phrase.text}") from last_error


async def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    CLIP_DIR.mkdir(parents=True, exist_ok=True)

    voice = await choose_voice()
    print(f"Selected voice: {voice}")

    master = AudioSegment.silent(duration=TOTAL_MS, frame_rate=SAMPLE_RATE)
    master = ensure_format(master)

    for seg_index, plan in enumerate(SEGMENTS, start=1):
        assembled = AudioSegment.silent(duration=0, frame_rate=SAMPLE_RATE)
        assembled = ensure_format(assembled)
        for phrase_index, phrase in enumerate(plan.phrases, start=1):
            path = CLIP_DIR / f"s{seg_index:02d}_p{phrase_index:02d}.mp3"
            clip = await synthesise_phrase(voice, phrase, path)
            assembled += clip
            if phrase.pause_ms:
                assembled += ensure_format(
                    AudioSegment.silent(duration=phrase.pause_ms, frame_rate=SAMPLE_RATE)
                )

        available_ms = plan.end_ms - plan.start_ms - plan.lead_ms - plan.tail_ms
        assembled = tempo_fit(assembled, available_ms, f"segment_{seg_index:02d}")
        assembled = assembled.fade_in(18).fade_out(35)
        overlay_at = plan.start_ms + plan.lead_ms
        master = master.overlay(assembled, position=overlay_at)
        print(
            f"Segment {seg_index}: window={plan.end_ms-plan.start_ms}ms, "
            f"voice={len(assembled)}ms, placed={overlay_at}ms"
        )

    master = effects.compress_dynamic_range(
        master,
        threshold=-22.0,
        ratio=2.0,
        attack=20.0,
        release=180.0,
    )
    master = master.high_pass_filter(70).low_pass_filter(14_000)
    master = master.fade_in(180).fade_out(260)
    master = ensure_format(master[:TOTAL_MS])

    wav_path = OUT_DIR / "earcodex_narration_za_female.wav"
    mp3_path = OUT_DIR / "earcodex_narration_za_female.mp3"
    master.export(wav_path, format="wav")
    master.export(mp3_path, format="mp3", bitrate="192k")

    (OUT_DIR / "voice_used.txt").write_text(
        f"{voice}\nSouth African English female narration; phrase-level pacing and prosody.\n",
        encoding="utf-8",
    )
    print(f"Wrote {wav_path} ({len(master)} ms)")
    print(f"Wrote {mp3_path}")


if __name__ == "__main__":
    asyncio.run(main())
