from fastapi import APIRouter, status, HTTPException, Depends
from pydantic import BaseModel
from TODO.models import Users
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from TODO.database import sesssionLocal
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta, datetime
from jose import jwt, JWTError

# ------------------------------
# Router config
# ------------------------------

router = APIRouter()

SECRET_KEY = "c10c59a6c97998ad11ab000d1305318442a3433278a9d173064929616f8e12d7"
ALGORITHM = "HS256"

# bcrypt_sha256 automatically pre-hashes passwords, removing bcrypt's 72-byte limit
bcrypt_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto"
)


oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")


# ------------------------------
# Database session dependency
# ------------------------------

def get_db():
    db = sesssionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


# ------------------------------
# Request / Response Schemas
# ------------------------------

class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str


# ------------------------------
# Authentication Helpers
# ------------------------------

def authenticated_user(username: str, password: str, db: Session):
    """Return the user object if authentication succeeds."""
    user = db.query(Users).filter(Users.username == username).first()

    if not user:
        return None

    if not bcrypt_context.verify(password, user.hashed_password):
        return None

    return user


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {
        "sub": username,
        "id": user_id,
        "role": role
    }
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        role: str = payload.get("role")

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user."
            )

        return {"username": username, "id": user_id}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized User."
        )


user_dependency = Annotated[dict, Depends(get_current_user)]


# ------------------------------
# Routes
# ------------------------------

@router.post("/auth/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):

    hashed_pw = bcrypt_context.hash(create_user_request.password)

    new_user = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=hashed_pw,
        role=create_user_request.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()

    return {"message": "User created successfully."}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency
):
    user = authenticated_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = await create_access_token(
        username=user.username,
        user_id=user.id,
        expires_delta=timedelta(minutes=20)
    )

    return {"access_token": access_token, "token_type": "bearer"}