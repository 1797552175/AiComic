#!/bin/bash
# 登录模块实现
cd /opt/AiComic/apps/backend
cat >> api/auth.py << 'EOF'
认证模块 - 登录
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix='/api/auth', tags=['auth'])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user_id: int

@router.post('/login', response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    token = create_access_token(user_id=user.id)
    return LoginResponse(access_token=token, user_id=user.id)
EOF
echo 'AUTH_LOGIN_DONE'
