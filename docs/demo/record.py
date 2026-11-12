import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from playwright.sync_api import Page, Route, sync_playwright

DEMO_PAGE = "https://farkad.web.app/try"
DEMO_ENDPOINT = "**/api/try"
SAID = "Two eggs, un grand verre d'eau, slept badly"
VIEWPORT = {"width": 560, "height": 900}
PIXEL_RATIO = 2
MARGIN_PIXELS = 24
FRAME_HEIGHT_PIXELS = 1100
GIF_WIDTH_PIXELS = 720
OPENING_SECONDS = 0.8
TYPING_SECONDS_PER_FRAME = 0.06
READING_SECONDS = 1.2
HOLD_SECONDS = 4.5
ANSWER_PATIENCE_MILLISECONDS = 30_000
HERE = Path(__file__).parent

Theme = Literal["light", "dark"]


@dataclass(frozen=True)
class Card:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Frames:
    folder: Path
    card: Card
    durations: list[float]

    def take(self, page: Page, seconds: float) -> None:
        page.screenshot(
            path=self.folder / f"{len(self.durations):04}.png",
            full_page=True,
            clip={
                "x": self.card.x - MARGIN_PIXELS,
                "y": self.card.y - MARGIN_PIXELS,
                "width": self.card.width + 2 * MARGIN_PIXELS,
                "height": FRAME_HEIGHT_PIXELS,
            },
        )
        self.durations.append(seconds)

    def concat_list(self) -> Path:
        lines = [
            f"file '{self.folder / f'{index:04}.png'}'\nduration {seconds}"
            for index, seconds in enumerate(self.durations)
        ]
        last = self.folder / f"{len(self.durations) - 1:04}.png"
        listed = self.folder / "frames.txt"
        listed.write_text("\n".join([*lines, f"file '{last}'"]) + "\n")
        return listed


def card_on(page: Page) -> Card:
    box = page.locator("#demo").evaluate(
        "card => { const r = card.getBoundingClientRect();"
        " return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; }"
    )
    return Card(**box)


def record(theme: Theme, folder: Path, answer: str | None) -> tuple[Frames, str]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport=VIEWPORT, device_scale_factor=PIXEL_RATIO, color_scheme=theme
        )
        if answer is not None:
            replayed = answer

            def replay(route: Route) -> None:
                route.fulfill(status=200, content_type="application/json", body=replayed)

            page.route(DEMO_ENDPOINT, replay)
        page.goto(DEMO_PAGE, wait_until="networkidle")
        page.locator("header.sticky").evaluate("header => header.remove()")
        page.locator("#demo").evaluate(
            "card => { for (let after = card.closest('section').nextElementSibling; after;"
            " after = after.nextElementSibling) after.style.visibility = 'hidden'; }"
        )
        frames = Frames(folder, card_on(page), [])
        frames.take(page, OPENING_SECONDS)
        field = page.locator("#try-utterance")
        for letter in SAID:
            field.press_sequentially(letter)
            frames.take(page, TYPING_SECONDS_PER_FRAME)
        with page.expect_response(DEMO_ENDPOINT) as answered:
            page.locator("#try-form button[type=submit]").click()
        frames.take(page, READING_SECONDS)
        body = answered.value.text()
        if '"entries"' not in body:
            sys.exit(f"the demo did not answer with entries: {body}")
        page.locator("#try-output article").first.wait_for(timeout=ANSWER_PATIENCE_MILLISECONDS)
        frames.take(page, HOLD_SECONDS)
        final = card_on(page)
        browser.close()
    if final.height + 2 * MARGIN_PIXELS > FRAME_HEIGHT_PIXELS:
        sys.exit(f"the answered card is taller than {FRAME_HEIGHT_PIXELS}px: {final.height}")
    return Frames(folder, final, frames.durations), body


def encode(frames: Frames, gif: Path) -> None:
    width = round((frames.card.width + 2 * MARGIN_PIXELS) * PIXEL_RATIO)
    height = round((frames.card.height + 2 * MARGIN_PIXELS) * PIXEL_RATIO)
    palette = "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=diff_mode=rectangle"
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(frames.concat_list()),
            "-vf", f"crop={width}:{height}:0:0,scale={GIF_WIDTH_PIXELS}:-1:flags=lanczos,{palette}",
            "-fps_mode", "vfr", "-loop", "0", str(gif),
        ],
        check=True,
    )  # fmt: skip


def main() -> None:
    answer: str | None = None
    themes: tuple[Theme, ...] = ("light", "dark")
    for theme in themes:
        with tempfile.TemporaryDirectory() as folder:
            frames, answer = record(theme, Path(folder), answer)
            encode(frames, HERE / f"{theme}.gif")
    print(json.dumps(json.loads(answer or "{}"), ensure_ascii=False))


if __name__ == "__main__":
    main()
