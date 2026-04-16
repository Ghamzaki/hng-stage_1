from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers.profiles import router as profiles_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles_router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.exception_handler(400)
async def bad_request_handler(request: Request, exc):
    return JSONResponse(status_code=400, content={"status": "error", "message": str(exc.detail)})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"status": "error", "message": str(exc.detail)})


@app.exception_handler(422)
async def unprocessable_handler(request: Request, exc):
    return JSONResponse(status_code=422, content={"status": "error", "message": "Invalid type"})


@app.exception_handler(502)
async def bad_gateway_handler(request: Request, exc):
    return JSONResponse(status_code=502, content={"status": "error", "message": str(exc.detail)})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})