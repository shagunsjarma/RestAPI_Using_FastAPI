from fastapi import FastAPI
from TODO import models
from TODO.database import engine
from TODO.routers import auth, todos

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(todos.router)
