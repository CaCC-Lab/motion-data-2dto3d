# Repository Guidelines

## Project Structure & Module Organization
This repository is currently spec-first. Implementation files are not scaffolded yet, so treat `.kiro/specs/video-motion-extraction/` as the source of truth.

- `.kiro/specs/video-motion-extraction/`: requirements (`requirements.md`), design (`design.md`), and implementation plan (`tasks.md`).
- `.cursor/rules/`: commit and PR message conventions.
- Planned Python package: `video_motion_extraction/` with modules such as `video_extractor.py`, `pose_estimator.py`, `data_processor.py`, `converter_3d.py`, `pipeline.py`, and `cli.py`.
- Put tests in `tests/`, mirroring module names (example: `tests/test_video_extractor.py`).

## Build, Test, and Development Commands
- `pytest`: run the full test suite.
- `pytest -m property`: run property-based tests only.
- `pytest tests/test_video_extractor.py::test_extract_frames`: run one targeted test.
- `python -m video_motion_extraction.cli input.mp4 --output output.bvh --format bvh`: run the CLI pipeline (after implementation).
- `rg --files` and `rg "pattern"`: fast file and text search during development.

## Coding Style & Naming Conventions
- Target Python 3.8+ with 4-space indentation.
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.
- Keep public APIs type-annotated; prefer `@dataclass` for core data models (`VideoMetadata`, `Pose2DSequence`, `Motion3DData`).
- Keep code aligned to pipeline stages (extract -> estimate -> process -> convert) and validate inputs early.

## Testing Guidelines
- Use `pytest` and `hypothesis`.
- Name files `test_<module>.py`; name tests `test_<expected_behavior>`.
- Cover unit tests and key invariants: frame-count preservation, joint-data consistency, finite angular velocity outputs, non-mutation of valid points during interpolation, and normalized quaternion rotations.
- Mock GPU-dependent components (MMPose, VideoPose3D) for deterministic unit tests.

## Commit & Pull Request Guidelines
- The current `master` branch has no commits; follow `.cursor/rules/commit-message-format.mdc` and `.cursor/rules/pr-message-format.mdc`.
- Commit format: `<type>: <summary>` using Conventional Commit types (`feat`, `fix`, `refactor`, `test`, `docs`, etc.), plus bullet points in the body.
- Project default is Japanese for commit/PR text unless a task explicitly requires another language.
- PRs should include: `Overview`, `Changes`, `Tests`, and related issues (`Refs:`/`Closes:`). Work on feature branches; avoid direct pushes to `main`/`master`.
