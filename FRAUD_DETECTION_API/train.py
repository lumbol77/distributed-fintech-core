import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler

# 1. Load Dataset
data = pd.read_csv("data/creditcard.csv") 

# 2. Select specific features for the Digital Wallet API
features_for_wallet = ["V1", "V2", "V3", "Amount"] 
X = data[features_for_wallet]
y = data["Class"]

# 3. Train-Test Split (Stratify keeps fraud ratio balanced)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 4. Scaling (The "Translator")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. Build & Train Model (Using Scaled Data)
model = RandomForestClassifier(
    n_estimators=50, 
    max_depth=10,            
    min_samples_leaf=5,       
    class_weight="balanced", 
    random_state=42
)
model.fit(X_train_scaled, y_train)

# 6. Evaluate Model (Using Scaled Test Data)
y_pred = model.predict(X_test_scaled)

print("\nModel Performance Metrics:")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1 Score:  {f1_score(y_test, y_pred):.4f}")
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# 7. Save BOTH artifacts for the Fraud API
os.makedirs("model", exist_ok=True)
joblib.dump(model, "model/fraud_model.pkl")
joblib.dump(scaler, "model/scaler.pkl") 

print("\nSuccess: Model and Scaler saved in model/ folder.")