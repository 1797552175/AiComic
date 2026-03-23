#!/bin/bash
# Token刷新模块
cd /opt/AiComic/apps/backend
cat >> api/auth.py << 'EOF'

class RefreshRequest(BaseModel):
    token: str

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'

@router.post('/refresh', response_model=RefreshResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get('sub'))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='用户不存在')
        new_token = create_access_token(user_id=user_id)
        return RefreshResponse(access_token=new_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token已过期')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='无效Token')
EOF
echo 'TOKEN_REFRESH_DONE'
