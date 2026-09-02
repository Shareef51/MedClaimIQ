from pathlib import Path
root=Path(__file__).resolve().parents[1]
required=[
 'backend/app/realtime/broker.py','backend/app/realtime/outbox.py','backend/app/realtime/consumer.py','backend/app/realtime/replay.py','backend/app/api/v1/realtime.py','backend/app/api/v1/fhir_subscription.py','backend/alembic/versions/0015_realtime_event_backbone.py','config/realtime_event_policy.json','docs/REAL_TIME_EVENT_DRIVEN_BACKBONE.md']
missing=[p for p in required if not (root/p).exists()]
if missing: raise SystemExit(f'missing realtime artifacts: {missing}')
text=(root/'docker-compose.yml').read_text()
for token in ['redpanda:v26.2.1','redpanda-console','19092:19092']:
    if token not in text: raise SystemExit(f'missing compose token {token}')
print('Realtime event-driven backbone architecture verified.')
