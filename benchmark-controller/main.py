from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional

from benchmark import NODES, run_full_benchmark, results_to_csv

app = FastAPI(title="ECIES Benchmark Controller")

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
    results: list


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "ECIES Benchmark Controller",
        "available_nodes": NODES,
        "endpoints": {
            "POST /benchmark": "Uruchom benchmark (body: BenchmarkRequest)",
            "GET  /results":   "Ostatnie wyniki w formacie JSON",
            "GET  /results/csv": "Ostatnie wyniki do pobrania jako CSV",
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
        return BenchmarkResponse(
            status="success",
            iterations=req.iterations,
            nodes_tested=nodes_tested,
            total_measurements=len(results),
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
