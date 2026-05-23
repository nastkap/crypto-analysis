from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional

from benchmark import NODES, run_full_benchmark, results_to_csv
from db import db_enabled, get_run, get_run_results, init_db, list_runs, save_run

app = FastAPI(title="ECIES Benchmark Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_results: list = []
_last_csv: str = ""
_is_running: bool = False


class BenchmarkRequest(BaseModel):
    iterations: int = Field(default=100, ge=1, le=10_000, description="Liczba iteracji (1–10000)")
    message: str = Field(
        default="Tajny tekst do testowania wydajnosci systemu ECIES",
        min_length=1,
        description="Wiadomość testowa",
    )
    nodes: Optional[list[str]] = Field(
        default=None,
        description="Lista węzłów do przetestowania. None = wszystkie",
    )


class BenchmarkResponse(BaseModel):
    status: str
    iterations: int
    nodes_tested: list[str]
    total_measurements: int
    run_id: Optional[str] = None
    stored_in_db: bool = False
    results: list


@app.on_event("startup")
def startup_event() -> None:
    try:
        init_db()
    except Exception as exc:
        print(f"[benchmark-controller] DB init error: {exc}", flush=True)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "ECIES Benchmark Controller",
        "database_enabled": db_enabled(),
        "available_nodes": NODES,
        "endpoints": {
            "POST /benchmark": "Uruchom benchmark (body: BenchmarkRequest)",
            "GET  /results":   "Ostatnie wyniki w formacie JSON",
            "GET  /results/csv": "Ostatnie wyniki do pobrania jako CSV",
            "GET  /runs": "Historia benchmarkow z bazy",
            "GET  /runs/{run_id}": "Szczegoly jednego uruchomienia",
            "GET  /runs/{run_id}/results": "Wyniki pomiarow z jednego uruchomienia",
        },
    }


@app.get("/health")
def health_check():
    """Health check endpoint dla Docker health checks"""
    return {"status": "healthy", "service": "ECIES Benchmark Controller"}


@app.post("/benchmark", response_model=BenchmarkResponse)
def run_benchmark(req: BenchmarkRequest):
    global _last_results, _last_csv, _is_running

    if _is_running:
        raise HTTPException(status_code=409, detail="Benchmark jest już uruchomiony. Poczekaj na wyniki.")

    if req.nodes is not None:
        unknown = [n for n in req.nodes if n not in NODES]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Nieznane węzły: {unknown}. Dostępne: {NODES}",
            )

    _is_running = True
    try:
        results = run_full_benchmark(
            message=req.message,
            iterations=req.iterations,
            selected_nodes=req.nodes,
        )
        _last_results = results
        _last_csv = results_to_csv(results)

        nodes_tested = list(dict.fromkeys(r["Biblioteka"] for r in results))

        run_id: Optional[str] = None
        stored_in_db = False
        try:
            run_id = save_run(
                iterations=req.iterations,
                message=req.message,
                nodes=nodes_tested,
                results=results,
            )
            stored_in_db = run_id is not None
        except Exception as db_exc:
            print(f"[benchmark-controller] DB save error: {db_exc}", flush=True)

        return BenchmarkResponse(
            status="success",
            iterations=req.iterations,
            nodes_tested=nodes_tested,
            total_measurements=len(results),
            run_id=run_id,
            stored_in_db=stored_in_db,
            results=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _is_running = False


@app.get("/results")
def get_results_json():
    if not _last_results:
        raise HTTPException(status_code=404, detail="Brak wyników. Uruchom najpierw POST /benchmark.")
    return {"total": len(_last_results), "results": _last_results}


@app.get("/results/csv", response_class=PlainTextResponse)
def get_results_csv():
    if not _last_csv:
        raise HTTPException(status_code=404, detail="Brak wyników. Uruchom najpierw POST /benchmark.")
    return PlainTextResponse(
        content=_last_csv,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=wyniki_benchmarku.csv"},
    )


@app.get("/runs")
def get_runs(
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Baza danych nie jest skonfigurowana (brak DATABASE_URL).")

    try:
        items = list_runs(limit=limit, offset=offset)
        return {"total": len(items), "runs": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Blad odczytu bazy: {exc}")


@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Baza danych nie jest skonfigurowana (brak DATABASE_URL).")

    try:
        item = get_run(run_id)
        if not item:
            raise HTTPException(status_code=404, detail="Nie znaleziono uruchomienia o podanym run_id.")
        return item
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Blad odczytu bazy: {exc}")


@app.get("/runs/{run_id}/results")
def get_run_results_endpoint(run_id: str):
    if not db_enabled():
        raise HTTPException(status_code=503, detail="Baza danych nie jest skonfigurowana (brak DATABASE_URL).")

    try:
        item = get_run(run_id)
        if not item:
            raise HTTPException(status_code=404, detail="Nie znaleziono uruchomienia o podanym run_id.")

        results = get_run_results(run_id)
        return {"run": item, "total": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Blad odczytu bazy: {exc}")
