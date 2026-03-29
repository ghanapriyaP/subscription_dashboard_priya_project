import os, time
if os.path.exists('subscriptions.db'):
    os.remove('subscriptions.db')

from database import engine, SessionLocal
import models
from auth import hash_password
from datetime import date, timedelta

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

email = f'smoke_{int(time.time())}@test.com'
u = models.User(email=email, hashed_password=hash_password('pass123'))
db.add(u); db.commit(); db.refresh(u)

sub = models.Subscription(
    user_id=u.id, tool_name='GitHub', purchase_date=date.today(),
    billing_cycle='monthly', renewal_date=date.today() + timedelta(days=5),
    cost=9.99, category='DevOps', status='active', currency='USD'
)
db.add(sub); db.commit()

class FakeUser:
    id = u.id

# Dashboard
from routers.dashboard import get_dashboard
r = get_dashboard(db=db, current_user=FakeUser())
assert r.total_subscriptions == 1
assert r.total_annual_cost == round(9.99 * 12, 2), f"Got {r.total_annual_cost}"
assert len(r.upcoming_renewals_7_days) == 1
assert r.spend_by_category[0].category == 'DevOps'
assert r.spend_by_billing_cycle['monthly'] == 9.99
print(f"  Dashboard OK: annual=${r.total_annual_cost}, 7d={len(r.upcoming_renewals_7_days)}, cats={len(r.spend_by_category)}")

# Analytics
from routers.analytics import get_analytics, get_spend_summary
a = get_analytics(db=db, current_user=FakeUser())
assert len(a.cost_optimization_tips) > 0
s = get_spend_summary(db=db, current_user=FakeUser())
assert s['active_tools'] == 1
assert s['daily_cost'] > 0
print(f"  Analytics OK: {len(a.cost_optimization_tips)} tips, daily=${s['daily_cost']}")

# Quick prompts
from routers.chat import QUICK_PROMPTS
assert len(QUICK_PROMPTS) == 8
print(f"  Quick prompts OK: {len(QUICK_PROMPTS)} prompts")

# Subscriptions filter
from routers.subscriptions import list_subscriptions
subs = list_subscriptions(
    status='active', category=None, billing_cycle=None, search=None,
    renewing_in_days=None, sort_by='cost', sort_order='desc',
    page=1, page_size=20, db=db, current_user=FakeUser()
)
assert len(subs) == 1
assert subs[0].days_until_renewal == 5
print(f"  Subscriptions filter OK: {len(subs)} subs, days_until_renewal={subs[0].days_until_renewal}")

db.close()
print("\nALL SMOKE TESTS PASSED")
