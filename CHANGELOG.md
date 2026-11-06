# Changelog

Every release, newest first, in the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
format. Before 1.0 a minor version may break the interface; each break is marked **Breaking**.

## [Unreleased]

## [0.26.0] - 2026-11-05

### Fixed

- **Breaking:** `Usage.step` is a string again. A `Usage` is stored, and the engine cannot know
  the consumer's `StrEnum` it was labelled with, so 0.25.0's stored usages did not parse back.

## [0.25.0] - 2026-11-05

### Added

- `VertexModel.choosing(choices)`: the same retrying client, asked with other tier choices, so a
  consumer builds one client with `connected(retries=)` and never a second retrying client.
- The example report shows how often the validators agreed with the gold set, each disagreement as
  a miss, and how many answers each model sent that did not parse.

### Changed

- **Breaking:** a recording is read and written as a typed `Recording`; a file with a missing or
  unknown field no longer replays.
- **Breaking:** `NoRecordedResponseError.because` is an `Unreachable`, never `None` or a string;
  its members replace `PROMPT_CHANGED` and `SCHEMA_CHANGED`.
- **Breaking:** `Usage.step` is the `StrEnum` the prompt was labelled with, not a string.
- **Breaking:** `EntryRecomputer` raises `ModelUnavailableError(output_did_not_parse)` when the
  model recomputes no entry, instead of returning no values beside a paid `Usage`.

### Removed

- **Breaking:** `VertexModel.connected(choices=)`: call `choosing` on the connected model.

## [0.24.0] - 2026-11-05

### Removed

- **Breaking:** the OpenAI and Anthropic adapters, and the `openai` and `anthropic` extras. Neither
  heard audio nor reasoned on a budget, so the README's voice and cascade rows held for Gemini
  alone; Gemini on Vertex AI is the one provider.
- **Breaking:** `ProviderModel` and `farkad_ai.models.provider`: `VertexModel` implements `Model`
  itself. `MissingCredentialsError` lives in `farkad_ai.models.factory`, and `PLACEHOLDER_INPUT`
  in `farkad_ai.models.vertex`.
- **Breaking:** `Unavailability.unsupported_request`, which only those adapters raised.

## [0.23.0] - 2026-11-05

### Added

- `CaptureScore.word_errors` and `RunScore.word_error_rate` score the transcript the engine heard
  against the case's utterance, ignoring case, punctuation and combining marks such as Arabic
  vowels, so a spoken gold set measures hearing beside routing and fields.
- `GoldCase.request(tracked)` builds the case's `CaptureRequest`; a consumer's case overrides it
  to ask with a clip instead of text.

### Changed

- **Breaking:** `score_capture` takes `heard`, the transcript the engine returned, and
  `CaptureScore` carries it.
- **Breaking:** `ProviderModel` takes its client type as a parameter, `ProviderModel[Client,
  Response]`, holds the client, and declares each tier's default model as `default_choices`. A
  provider no longer writes a constructor; the module-level `DEFAULT_CHOICES` are gone.
- **Breaking:** `ProviderModel[Client, Response, Refusal]` turns the provider's `refused_by`
  error into `provider_refused` and missing token counts into `usage_not_reported` itself: a
  provider implements `_tokens` instead of `_usage`, and `vertex.usage_of` is gone.

## [0.22.0] - 2026-10-25

### Added

- `farkad-ai prompts` lists every prompt the engine ships, with its version.

### Removed

- **Breaking:** `TwoPassCaptureEngine` no longer takes `routing_prompt` or `extraction_prompt`;
  `Router`, `PillarExtractor`, `EntryRecomputer` and `MemoryInferrer` no longer take
  `instructions`; `routing_instructions`, `prompt()` and `list_prompts()` no longer take an asset
  or a folder. Each stage asks with the prompt it ships.

### Changed

- A prompt's `instructions_version` follows what the model is asked before the per-call words:
  routing hashes its rendered catalogue and rules, extraction and recompute the template with
  the pillar's title, guidance and examples. Re-record the eval after upgrading.
- The answer schema carries only model-facing words: `PassOne`'s and `TimeHint`'s docstrings
  lost their developer notes.

### Fixed

- Pass one no longer logs a thing named only to say when another happened: "stretching after
  training" and "estiramientos después de correr" log the stretching alone.
- `farkad-ai route` requires `--text`, and stops with its usage before any model is created
  instead of routing an empty sentence.
- CI passes again: the core-only leg type-checks the Vertex retry test.
- The README's cascade row says a failed topic is asked again on the standard tier, a stronger
  model or the same one given time to reason, and the measured table names its example topics.

## [0.21.0] - 2026-10-18

### Changed

- Each provider builds its own client: `VertexModel.connected(retries=...)`, and
  `ProviderModel` is typed by its response.
- **Breaking:** `memory.habits.Logged` is `Occurrence`, and `MissingCredentialsError` lives in
  `farkad_ai.models.provider`.

## [0.20.0] - 2026-10-18

### Added

- Entry recompute (`EntryRecomputer`) and habit counting (`baselines_from`).

### Changed

- **Breaking:** `core_sheet` no longer takes `habit_window`.

## [0.19.0] - 2026-10-16

### Changed

- Things named side by side stay separate mentions; only what the user said went into something
  is part of it.

## [0.18.0] - 2026-10-16

### Added

- A consumer's rules for where its pillars meet: `routing_rules=` on `TwoPassCaptureEngine` and
  `evaluate`, `rules=` on `Router`, rendered once after the pillar list.

## [0.17.0] - 2026-10-16

### Changed

- **Breaking:** the package root re-exports nothing; escalation is
  `PillarExtractor.extract_escalating`; `NothingToLog` is the one empty outcome.
- Pass one reports `states_a_lasting_fact`; `MemoryInferrer.infer(said, known, *, switched_off)`
  returns statements with an end and `asked_to_remember`; the memory sheet renders every fact in
  a marked data block.

## [0.16.0] - 2026-10-16

### Changed

- Prompts state principles, never the gold set's sentences, and the routing prompt names no
  pillar: their meaning comes from the consumer's catalogue.
- **Breaking:** `StatedTime.time_of_day` is the hour the user said or a `PartOfDay`, never a
  guessed clock. A category the user named is kept: `label_fields` are discriminators only.

### Added

- `photo_briefing(language)`.

## [0.15.0] - 2026-10-16

### Changed

- **Breaking:** the eval reports tokens, not cents, so any provider can be measured; one
  `evaluate(model, catalogue, tracked, cases)` runner, whose `GoldCase` a consumer can extend.
- A pillar declares its `label_fields`; the memory vocabulary, the content and fact limits and
  the habit window are passed in by the consumer; a recorder's `commit()` replaces its
  recordings.

## [0.14.0] - 2026-10-15

### Changed

- **Breaking:** an interface is named for its role and an implementation for how it plays it:
  `ModelPort` is `Model`, `CaptureEnginePort` is `CaptureEngine` (implemented by
  `TwoPassCaptureEngine`), `PillarSpecProtocol` is `PillarSpec`; `farkad_ai.types` moves into
  `farkad_ai.models.port`.
- Glass and cup words are named in four languages, so كأسين is 500 ml.

## [0.13.0] - 2026-10-15

### Changed

- **Breaking:** each stage has one boundary module, `port.py`; behaviour is unchanged.

## [0.12.0] - 2026-10-14

### Changed

- A stated time belongs to the mention it was said about, so "coffee at 8" no longer dates last
  night's sleep.

## [0.11.0] - 2026-10-12

### Added

- `farkad-ai eval` measures routing, field accuracy and cost per capture in five language
  groups.

### Fixed

- Transcripts are copied character for character in every language.
- The Anthropic and OpenAI adapters type-check against their SDKs.

## [0.10.0] - 2026-10-11

### Changed

- **Breaking:** one refusal type, `PillarRefused`; `FallbackModel` is gone; `create_model` takes a
  provider and a fixtures directory.

## [0.9.1] - 2026-10-10

### Fixed

- A subject the model answers matches a known one regardless of case, so a fact the user typed is
  never overwritten by a duplicate.
- The memory sheet keeps every line that fits instead of stopping at the first that does not.

## [0.9.0] - 2026-10-10

### Changed

- **Breaking:** one `CaptureEngine` over the pillars a consumer tracks replaces
  `TwoPassPipeline`, and `TrackedPillar` is what a consumer supplies for extraction.
- A recording's fingerprint carries the answer schema, so earlier recordings must be re-made.

## [0.8.0] - 2026-10-10

### Changed

- **Breaking:** the core imports no provider SDK; `ModelChoice(model, reasoning)` replaces
  `TierChoice(model, thinking_budget)`, and an adapter refuses a reasoning level it cannot honour.

### Removed

- The demo, recompute and photo prompts.

## [0.7.0] - 2026-10-02

### Removed

- Unused public names and the unused pipeline observer.

### Fixed

- Log fields that had been dropped are logged again.

## [0.6.0] - 2026-10-01

### Added

- `Usage.input_modality`: text, audio or image.

### Changed

- **Breaking:** each `ExtractedEntry` carries its own findings, so one implausible entry no longer
  marks its siblings stale.

## [0.5.1] - 2026-10-01

### Fixed

- The demo prompt describes an answer keyed by pillar and field id.

## [0.5.0] - 2026-10-01

### Changed

- **Breaking:** pass one returns `mentions`, each thing said and the one pillar that records it;
  each specialist is handed only its own.

## [0.4.0] - 2026-09-30

### Removed

- **Breaking:** commercial pricing, `cost_cents` and `pricing.py`.

## [0.3.0] - 2026-09-29

### Changed

- **Breaking:** tier choices are asked on every call, so the model behind a tier changes without
  a restart; `RecordedModel` refuses an answer recorded from another model than the one pinned.

## [0.2.0] - 2026-09-29

### Added

- Two passes: one call routes a sentence, recording or photo; one call per topic extracts it.
- Gemini on Vertex AI, Claude and OpenAI behind one interface; long-term memory; an offline eval
  on recorded answers; the `farkad-ai` command.

[Unreleased]: https://github.com/brmel/farkad-ai/compare/v0.26.0...HEAD
[0.26.0]: https://github.com/brmel/farkad-ai/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/brmel/farkad-ai/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/brmel/farkad-ai/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/brmel/farkad-ai/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/brmel/farkad-ai/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/brmel/farkad-ai/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/brmel/farkad-ai/compare/v0.19.0...v0.20.0
[0.19.0]: https://github.com/brmel/farkad-ai/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/brmel/farkad-ai/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/brmel/farkad-ai/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/brmel/farkad-ai/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/brmel/farkad-ai/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/brmel/farkad-ai/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/brmel/farkad-ai/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/brmel/farkad-ai/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/brmel/farkad-ai/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/brmel/farkad-ai/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/brmel/farkad-ai/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/brmel/farkad-ai/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/brmel/farkad-ai/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/brmel/farkad-ai/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/brmel/farkad-ai/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/brmel/farkad-ai/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/brmel/farkad-ai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/brmel/farkad-ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/brmel/farkad-ai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/brmel/farkad-ai/releases/tag/v0.2.0
