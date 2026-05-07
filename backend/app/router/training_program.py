from pydantic import BaseModel, Field
from fastapi import APIRouter, Body, HTTPException

from app.core.success_response import success_response
from app.services.training_program_service import (
    delete_training_program_vectors,
    get_import_status,
    import_training_program_batch,
    import_training_program_file,
    scan_training_program_files,
)


training_program_router = APIRouter(prefix="/api/training-program", tags=["training-program"])


class TrainingProgramImportRequest(BaseModel):
    relativePath: str
    force: bool = False


class TrainingProgramBatchImportRequest(BaseModel):
    relativePaths: list[str] = Field(default_factory=list)
    force: bool = False


@training_program_router.get("/files")
async def list_training_program_files():
    files = await scan_training_program_files()
    return success_response(data={"files": files})


@training_program_router.post("/import")
async def import_training_program(payload: TrainingProgramImportRequest):
    try:
        result = await import_training_program_file(payload.relativePath, force=payload.force)
        return success_response(data={"file": result})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@training_program_router.post("/import-batch")
async def import_training_program_files(payload: TrainingProgramBatchImportRequest):
    if not payload.relativePaths:
        raise HTTPException(status_code=400, detail="relativePaths cannot be empty")
    result = await import_training_program_batch(payload.relativePaths, force=payload.force)
    return success_response(data=result)


@training_program_router.delete("/import")
async def delete_training_program_import(payload: TrainingProgramImportRequest = Body(...)):
    try:
        result = await delete_training_program_vectors(payload.relativePath)
        return success_response(data=result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@training_program_router.get("/import-status")
async def training_program_import_status():
    return success_response(data=await get_import_status())
