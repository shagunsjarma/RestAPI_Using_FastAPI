from typing import Annotated
from sqlalchemy.orm import Session, sessionmaker
from fastapi import APIRouter, Depends, status, Path, HTTPException
from TODO.models import Todos
from TODO.database import engine, sesssionLocal
from TODO.routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()


def get_db():
    db = sesssionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def TodoRequest(BaseModel):
    title: str
    description: str
    priority: int
    complete: bool


@router.get("/")
async def get_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed.")
    return db.query(Todos).filter(Todos.owner_id == user.get('id')).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def get_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="UnAuthorized User.")
    todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).first()
    if todo_model is not None:
        return todo_model
    return HTTPException(status_code=404, detail='Todo not found.')


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(db: db_dependency, todo_request: TodoRequest):
    todo_model = Todos(**todo_request.dict())
    db.add(todo_model)
    db.commit()


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='UnAuthorized User.')
    todo_model = db.query(Todos).filter(todo_id == Todos.id).filter(Todos.owner_id == user.get('id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found.")
    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    db.add(todo_model)
    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="UnAuthorized User.")
    todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('get')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo is not found.")
    db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).delete()
    db.commit()
