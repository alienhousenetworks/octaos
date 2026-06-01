import sys
from app.db.session import SessionLocal
from app.api.v1.endpoints.dashboard import get_dashboard_metrics

db = SessionLocal()
try:
    print(get_dashboard_metrics(db=db, tenant_id="some_id"))
except Exception as e:
    import traceback
    traceback.print_exc()
