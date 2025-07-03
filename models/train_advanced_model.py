# ============================
# train_advanced_model.py (MySQLdb version)
# ============================

import MySQLdb
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import pickle

# --- DB CONFIG ---
DB_HOST = 'localhost'
DB_USER = 'lord'
DB_PASS = '2005'   # ✅ Replace with your actual password
DB_NAME = 'fitness_ai'   # ✅ Replace with your actual database

# --- CONNECT ---
db = MySQLdb.connect(
    host=DB_HOST,
    user=DB_USER,
    passwd=DB_PASS,
    db=DB_NAME
)

cursor = db.cursor()

# --- QUERY ---
query = """
    SELECT 
      p.weight,
      p.calories,
      p.protein,
      p.carbs,
      p.fat,
      p.duration,
      p.steps,
      u.age,
      u.gender,
      u.height
    FROM progress p
    JOIN users u ON p.user_id = u.id
"""

cursor.execute(query)
rows = cursor.fetchall()

columns = ['weight', 'calories', 'protein', 'carbs', 'fat',
           'duration', 'steps', 'age', 'gender', 'height']

df = pd.DataFrame(rows, columns=columns)

print(f"✅ Retrieved {len(df)} rows before cleaning")

# --- CLEAN ---
df = df.fillna({
    'age': df['age'].mean(),
    'height': df['height'].mean(),
    'weight': df['weight'].mean(),
    'calories': df['calories'].mean(),
    'protein': df['protein'].mean(),
    'carbs': df['carbs'].mean(),
    'fat': df['fat'].mean(),
    'duration': df['duration'].mean(),
    'steps': df['steps'].mean(),
    'gender': 'male'
})
df = df.dropna()

print(f"✅ Rows after cleaning: {len(df)}")

if df.empty:
    print("❌ No valid data left. Please add more progress records.")
    exit()

# --- FEATURE ENCODE ---
df['gender_num'] = df['gender'].apply(lambda g: 1 if str(g).lower() == 'male' else 0)

X = df[['age', 'gender_num', 'height', 'weight', 'calories',
        'protein', 'carbs', 'fat', 'duration', 'steps']]
y = df['weight']

# --- SPLIT ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- TRAIN ---
model = GradientBoostingRegressor()
model.fit(X_train, y_train)

# --- TEST ---
preds = model.predict(X_test)
mse = mean_squared_error(y_test, preds)
rmse = np.sqrt(mse)

print(f"✅ Model RMSE: {rmse:.2f}")

# --- SAVE ---
with open('advanced_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Model saved as advanced_model.pkl")

# --- CLEANUP ---
cursor.close()
db.close()
