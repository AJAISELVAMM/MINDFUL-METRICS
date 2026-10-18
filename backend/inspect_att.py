from app.database import engine
from sqlalchemy import inspect

insp = inspect(engine)
cols = [c["name"] for c in insp.get_columns("attendance")]
print("ATTENDANCE COLUMNS:", cols)
