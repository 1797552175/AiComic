#!/bin/bash
cd /opt/AiComic/apps/backend
cat >> api/users.py << 'EOF'

class UserProfile(BaseModel):
    id: int
    username: str
    email: str

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None

@router.get('/me', response_model=UserProfile)
def get_me(db: Session = Depends(get_db), token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail='未提供Token')
    try:
        payload = jwt.decode(token.replace('Bearer ', ''), SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get('sub'))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='用户不存在')
        return UserProfile(id=user.id, username=user.username, email=user.email)
    except:
        raise HTTPException(status_code=401, detail='无效Token')

@router.patch('/me', response_model=UserProfile)
def update_me(update: UserProfileUpdate, db: Session = Depends(get_db), token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail='未提供Token')
    try:
        payload = jwt.decode(token.replace('Bearer ', ''), SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get('sub'))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='用户不存在')
        if update.email:
            user.email = update.email
        db.commit()
        return UserProfile(id=user.id, username=user.username, email=user.email)
    except:
        raise HTTPException(status_code=401, detail='无效Token')
EOF
echo USER_INFO_DONE
