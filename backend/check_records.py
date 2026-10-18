from app.database import SessionLocal
from app.models import Attendance

db = SessionLocal()
count = db.query(Attendance).count()
print("Attendance record count:", count)
samples = db.query(Attendance).order_by(Attendance.id.desc()).limit(5).all()
for a in samples:
    print(f"ID={a.id}, Emp={a.employee_id}, Date={a.date}, in={a.check_in}, out={a.check_out}, final_status={a.final_status}, min={a.working_minutes}")
db.close()
