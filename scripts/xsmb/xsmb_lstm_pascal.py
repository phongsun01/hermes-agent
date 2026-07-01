"""
XSMB LSTM with Pascal Feature Integration
=========================================
Dự đoán chuỗi số xổ số bằng LSTM kết hợp tính năng cầu Pascal.
Mỗi ngày sẽ có input vector 200 chiều:
  - 100 chiều đầu: các số đã ra hôm nay (Presence Vector)
  - 100 chiều sau: dự đoán cầu Pascal từ hôm qua (One-hot Vector)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import sqlite3
import json
import os
import random
import datetime

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Device: {DEVICE}")

# 1. Hàm tính cầu Pascal
def pascal_prediction(db: int, g1: int):
    s = str(db).zfill(5) + str(g1).zfill(5)
    digits = [int(c) for c in s]
    while len(digits) > 2:
        digits = [(digits[i] + digits[i+1]) % 10 for i in range(len(digits)-1)]
    return f"{digits[0]}{digits[1]}"

# 2. Dataset & Model
class LotteryDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self): return len(self.X)
    def __getitem__(self, idx): return self.X[idx], self.y[idx]

class LotteryLSTMPascal(nn.Module):
    """
    Kiến trúc LSTM nhận input 200 chiều (100 chiều thực tế + 100 chiều Pascal)
    """
    def __init__(self, input_size=200, hidden_size=128, num_layers=2, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size, hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )
        self.attn = nn.Linear(hidden_size * 2, 1)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 100),
            nn.Sigmoid()
        )

    def forward(self, x):
        out, _ = self.lstm(x)             # (B, T, H*2)
        w = torch.softmax(self.attn(out), dim=1)   # (B, T, 1)
        ctx = (out * w).sum(dim=1)        # (B, H*2)
        return self.fc(ctx)               # (B, 100)

# 3. Load và tiền xử lý dữ liệu từ SQLite
def load_data_from_db():
    db_path = os.path.join(os.path.dirname(__file__), "xsmb_results.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at {db_path}")
        
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at ASC", conn)
    conn.close()
    
    n_days = len(df)
    if n_days < 15:
        raise ValueError("Need at least 15 days of historical data to run LSTM.")
        
    # Tạo presence matrix cho kết quả thực tế
    actual_matrix = np.zeros((n_days, 100), dtype=np.float32)
    pascal_matrix = np.zeros((n_days, 100), dtype=np.float32)
    
    for i, row in df.iterrows():
        # Phân tích các số thực tế
        numbers = []
        for col in ['gdb', 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7']:
            numbers.extend([int(num[-2:]) for num in row[col].split() if num])
        for num in numbers:
            actual_matrix[i, num] = 1.0
            
        # Tính cầu Pascal của ngày i-1 để làm input cho ngày i
        if i > 0:
            prev_row = df.iloc[i-1]
            prev_db = int(prev_row['gdb'].split()[0])
            prev_g1 = int(prev_row['g1'].split()[0])
            p_num = int(pascal_prediction(prev_db, prev_g1))
            pascal_matrix[i, p_num] = 1.0
            
    # Kết hợp 2 matrix thành input 200 chiều
    input_matrix = np.concatenate([actual_matrix, pascal_matrix], axis=1) # shape (N, 200)
    
    return input_matrix, actual_matrix

def make_sequences(input_matrix, actual_matrix, window=14):
    X, y = [], []
    for i in range(window, len(input_matrix)):
        X.append(input_matrix[i - window:i])
        y.append(actual_matrix[i])
    return np.array(X), np.array(y)

# 4. Train và Evaluate
def train_model(model, loader, optimizer, criterion):
    model.train()
    total_loss = 0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
        optimizer.zero_grad()
        pred = model(X_batch)
        loss = criterion(pred, y_batch)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

def run_lstm_pascal_pipeline(window=14, epochs=30, batch_size=4):
    print("[PIPELINE] Loading data from database...")
    input_matrix, actual_matrix = load_data_from_db()
    
    X, y = make_sequences(input_matrix, actual_matrix, window=window)
    print(f"[DATA] Sequence generated: X shape {X.shape}, y shape {y.shape}")
    
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    train_dataset = LotteryDataset(X_train, y_train)
    val_dataset = LotteryDataset(X_val, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    model = LotteryLSTMPascal().to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    criterion = nn.BCELoss()
    
    print(f"[TRAIN] Training model for {epochs} epochs...")
    for epoch in range(1, epochs + 1):
        loss = train_model(model, train_loader, optimizer, criterion)
        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:2d}/{epochs} | Loss: {loss:.4f}")
            
    # Dự đoán cho ngày kế tiếp (hôm nay)
    model.eval()
    last_sequence = input_matrix[-window:]
    last_sequence_tensor = torch.tensor([last_sequence], dtype=torch.float32).to(DEVICE)
    
    with torch.no_grad():
        pred_probs = model(last_sequence_tensor).cpu().numpy()[0]
        
    top10 = np.argsort(pred_probs)[-10:][::-1]
    
    print("\n=========================================")
    print("HYBRID PREDICTION RESULTS (LSTM + PASCAL):")
    print("Top 10 most potential numbers:")
    for rank, num in enumerate(top10):
        print(f"  Top {rank+1}: {num:02d} (Model probability: {pred_probs[num]*100:.2f}%)")
    print("=========================================")
    
    return top10

if __name__ == '__main__':
    try:
        run_lstm_pascal_pipeline()
    except Exception as e:
        print(f"Error: {e}")
