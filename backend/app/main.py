from fastapi import FastAPI

from app.routers import auth, follows, posts, feed

app = FastAPI(title="Intentional Social")

app.include_router(auth.router)
app.include_router(follows.router)
app.include_router(posts.router)
app.include_router(feed.router)


@app.get("/health")
def health():
    return {"status": "ok"}