from app.database import Session
from app.seed import seed

if __name__=='__main__':
    with Session() as db:seed(db)
    print('Seed complete. Demo login: admin@retail.local (password from SEED_PASSWORD or README).')
