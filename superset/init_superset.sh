#!/bin/sh
set -e

superset db upgrade

superset fab create-admin \
  --username "$SUPERSET_ADMIN_USERNAME" \
  --firstname Admin \
  --lastname User \
  --email admin@example.com \
  --password "$SUPERSET_ADMIN_PASSWORD"

superset init

# Inject the real DB password (export ZIP masks it as XXXXXXXXXX)
python3 - << 'PYEOF'
import zipfile, os

src = '/app/superset_config/dashboards/krooniliste_haiguste_ja_ilma_analuus.zip'
out = '/tmp/dashboard_fixed.zip'
user = os.environ.get('POSTGRES_USER', 'postgres').encode()
pw   = os.environ.get('POSTGRES_PASSWORD', 'postgres').encode()

with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, 'w') as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename.endswith('.yaml'):
            import re
            data = re.sub(
                rb'postgresql\+psycopg2://[^:]+:XXXXXXXXXX@',
                b'postgresql+psycopg2://' + user + b':' + pw + b'@',
                data
            )
        zout.writestr(item, data)

print('Password injected into dashboard ZIP')
PYEOF

superset import-dashboards -p /tmp/dashboard_fixed.zip -u "$SUPERSET_ADMIN_USERNAME"
echo "Dashboard imported successfully"
