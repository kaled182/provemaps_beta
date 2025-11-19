from django.db import connection

cursor = connection.cursor()
cursor.execute(
    "SELECT indexname, indexdef FROM pg_indexes "
    "WHERE tablename = 'zabbix_api_site' AND indexname = 'idx_site_location'"
)
result = cursor.fetchall()

if result:
    print("Index found:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
else:
    print("Index NOT found")

cursor.execute(
    "SELECT indexname FROM pg_indexes WHERE tablename = 'zabbix_api_site'"
)
all_idx = cursor.fetchall()
print(f"\nAll indexes ({len(all_idx)}):")
for idx in all_idx:
    print(f"  - {idx[0]}")
