import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import music21

from processing.bass_extractor import AmbiguousBassError, BassExtractor, NoBassPartError
from processing.fret_assigner import FretAssigner, detect_string_count
from processing.input_router import InputRouter, UnsupportedFormatError
from processing.lilypond_renderer import LilyPondRenderer
from processing.music_parser import MusicParser
from processing.musescore_exporter import MuseScoreExporter
from processing.omr import AudiverisOMR


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_PART_SELECTION = "awaiting_part"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    error: str = ""
    pdf_path: Path | None = None
    score_path: Path | None = None
    part_candidates: list[str] = field(default_factory=list)
    musicxml_path: Path | None = None
    title: str = ""
    num_strings: int | None = None
    export_musescore: bool = True


JOBS: dict[str, Job] = {}

TMP_ROOT = Path("tmp")
TOOLS_DIR = Path("tools")


def new_job() -> Job:
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id)
    JOBS[job_id] = job
    return job


def run_pipeline(
    job_id: str,
    input_path: Path,
    num_strings: int | None,
    export_musescore: bool,
    part_name: str | None = None,
) -> None:
    """Execute full pipeline. Called from background task."""
    job = JOBS[job_id]
    job.status = JobStatus.RUNNING
    job.num_strings = num_strings
    job.export_musescore = export_musescore

    tmp_dir = TMP_ROOT / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Normalize to MusicXML
        if job.musicxml_path is None:
            suffix = input_path.suffix.lower()
            if suffix == ".pdf":
                jar = TOOLS_DIR / "audiveris.jar"
                omr = AudiverisOMR(jar_path=jar, tmp_dir=tmp_dir / "omr")
                mxl_path = omr.run(input_path)
                router = InputRouter(tmp_dir=tmp_dir / "routed")
                musicxml_path = router.route(mxl_path)
            else:
                router = InputRouter(tmp_dir=tmp_dir / "routed")
                musicxml_path = router.route(input_path)
            job.musicxml_path = musicxml_path

        # Step 2: Parse + extract bass part
        parser = MusicParser()
        score = parser.parse(job.musicxml_path)
        job.title = (
            str(score.metadata.title or input_path.stem)
            if score.metadata
            else input_path.stem
        )

        extractor = BassExtractor()
        try:
            notes = extractor.extract(score, part_name=part_name)
        except NoBassPartError:
            parts = parser.list_parts(score)
            if len(parts) == 1:
                notes = extractor.extract(score, part_name=parts[0])
            elif len(parts) > 1:
                job.status = JobStatus.AWAITING_PART_SELECTION
                job.part_candidates = parts
                return
            else:
                raise
        except AmbiguousBassError as e:
            job.status = JobStatus.AWAITING_PART_SELECTION
            job.part_candidates = e.candidates
            return

        # Step 3: Assign frets
        strings = num_strings or detect_string_count(notes)
        fa = FretAssigner(num_strings=strings)
        assigned = fa.assign(notes)

        # Step 4: Render PDF
        renderer = LilyPondRenderer(tmp_dir=tmp_dir / "lily", num_strings=strings)
        pdf_path = renderer.render(assigned, title=job.title)
        job.pdf_path = pdf_path

        # Step 5: Export MuseScore (optional)
        if export_musescore:
            exporter = MuseScoreExporter(tmp_dir=tmp_dir / "musescore")
            job.score_path = exporter.export(score)

        job.status = JobStatus.DONE

    except Exception as e:
        job.status = JobStatus.ERROR
        job.error = str(e)
