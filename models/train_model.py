# train_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# Example data (normally you'd have real user data!)
data = {
    'weight': [70, 72, 75, 68, 67, 90, 92, 95, 88, 87],
    'calories': [1800, 2000, 2200, 1700, 1600, 3000, 3200, 3500, 2800, 2700],
    'goal': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],  # 0 = Weight Loss, 1 = Weight Gain
    'on_track': [1, 0, 0, 1, 1, 1, 0, 0, 1, 1]  # Label: 1 = On Track, 0 = Off Track
}

df = pd.DataFrame(data)

# Features & target
X = df[['weight', 'calories', 'goal']]
y = df['on_track']

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Save model
with open('progress_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as progress_model.pkl")
