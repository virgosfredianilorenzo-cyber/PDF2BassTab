import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from api.pipeline import JOBS, JobStatus, new_job, run_pipeline

app = FastAPI(title="PDF2BassTab")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

TMP_ROOT = Path("tmp")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    strings: int = Form(default=0),
    export_musescore: bool = Form(default=True),
):
    job = new_job()
    input_dir = TMP_ROOT / job.job_id / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / file.filename

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    num_strings = strings if strings in (4, 5) else None
    background_tasks.add_task(
        run_pipeline, job.job_id, input_path, num_strings, export_musescore
    )

    return templates.TemplateResponse(
        "result.html",
        {"request": request, "job": job},
    )


@app.get("/status/{job_id}", response_class=HTMLResponse)
async def status(request: Request, job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("<p>Job inconnu</p>", status_code=404)
    return templates.TemplateResponse(
        "result.html", {"request": request, "job": job}
    )


@app.post("/select-part/{job_id}", response_class=HTMLResponse)
async def select_part(
    request: Request,
    job_id: str,
    background_tasks: BackgroundTasks,
    part_name: str = Form(...),
):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("<p>Job inconnu</p>", status_code=404)

    input_dir = TMP_ROOT / job_id / "input"
    input_files = list(input_dir.iterdir())
    if not input_files:
        return HTMLResponse("<p>Fichier introuvable</p>", status_code=404)

    job.status = JobStatus.RUNNING
    job.part_candidates = []
    background_tasks.add_task(
        run_pipeline, job_id, input_files[0],
        job.num_strings, job.export_musescore, part_name
    )
    return templates.TemplateResponse(
        "result.html", {"request": request, "job": job}
    )


@app.get("/download/{job_id}/{filename}")
async def download(job_id: str, filename: str):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("Job inconnu", status_code=404)

    if filename == "tab.pdf" and job.pdf_path and job.pdf_path.exists():
        return FileResponse(job.pdf_path, filename="tablature.pdf")

    if filename == "score" and job.score_path and job.score_path.exists():
        ext = job.score_path.suffix
        return FileResponse(job.score_path, filename=f"score{ext}")

    return HTMLResponse("Fichier non disponible", status_code=404)
