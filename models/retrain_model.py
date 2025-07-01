import MySQLdb
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

# DB connection — adjust your creds!
db = MySQLdb.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    passwd=os.getenv('DB_PASS'),
    db=os.getenv('DB_NAME')
)
cursor = db.cursor(MySQLdb.cursors.DictCursor)

# Get joined progress data + user goals
cursor.execute('''
    SELECT p.weight, p.calories, u.goal
    FROM progress p
    JOIN users u ON p.user_id = u.id
''')
rows = cursor.fetchall()

# If no data yet, exit
if len(rows) < 5:
    print("❌ Not enough data to retrain.")
    exit()

# Build DataFrame
df = pd.DataFrame(rows)

# Convert goal text to numeric: 0 = loss, 1 = gain
df['goal_num'] = df['goal'].apply(lambda x: 0 if 'loss' in x.lower() else 1)

# Fake labels: For now, assume if calories < 2000 and goal is loss => on track
# You can replace this with actual user feedback later!
df['on_track'] = df.apply(lambda row: 1 if (row['goal_num'] == 0 and row['calories'] < 2000) else 0, axis=1)

# Train model
X = df[['weight', 'calories', 'goal_num']]
y = df['on_track']

model = RandomForestClassifier()
model.fit(X, y)

# Save updated model
with open('progress_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Model retrained & saved as progress_model.pkl")
