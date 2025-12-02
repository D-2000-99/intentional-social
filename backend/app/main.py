from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, follows, posts, feed, connections

app = FastAPI(title="Intentional Social")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth.router)
app.include_router(follows.router)
app.include_router(posts.router)
app.include_router(feed.router)
app.include_router(connections.router)


@app.get("/health")
def health():
    return {"status": "ok"}