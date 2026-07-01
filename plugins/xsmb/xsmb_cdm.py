"""
XSMB Prediction using Compound Dirichlet Multinomial (CDM) Model
==================================================================
Based on arXiv:2403.12836: "Predicting Winning Lottery Numbers"
"""

import numpy as np
import pandas as pd
import sqlite3
import os

def estimate_dirichlet_multinomial(X, M=27, K=100):
    """
    X: matrix shape (n, K)
    M: 27
    K: 100
    """
    n = len(X)
    if n < 2:
        return np.ones(K) * 0.1, 1.0
        
    P = X / float(M)
    pi = np.mean(P, axis=0)
    S2 = np.var(P, axis=0, ddof=1)
    
    alpha_0_estimates = []
    for j in range(K):
        mean_j = pi[j]
        var_j = S2[j]
        
        if mean_j > 0 and mean_j < 1 and var_j > 0:
            numerator = mean_j * (1.0 - mean_j) - var_j
            denominator = var_j - (mean_j * (1.0 - mean_j)) / float(M)
            if abs(denominator) > 1e-6:
                alpha_0_j = numerator / denominator
                if alpha_0_j > 0:
                    alpha_0_estimates.append(alpha_0_j)
                    
    if len(alpha_0_estimates) > 0:
        alpha_0 = np.median(alpha_0_estimates)
    else:
        alpha_0 = 1.0
        
    alpha_0 = np.clip(alpha_0, 0.1, 100.0)
    alpha = pi * alpha_0
    return alpha, alpha_0

def cdm_prediction(db_path, last_days=30):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
        
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT ngay, gdb, g1, g2, g3, g4, g5, g6, g7 FROM xsmb ORDER BY created_at DESC LIMIT ?", conn, params=(last_days,))
    conn.close()
    
    df = df.iloc[::-1].reset_index(drop=True)
    n_days = len(df)
    if n_days == 0:
        raise ValueError("Database is empty!")
        
    X = np.zeros((n_days, 100), dtype=np.float32)
    for i, row in df.iterrows():
        numbers = []
        for col in ['gdb', 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7']:
            numbers.extend([int(num[-2:]) for num in row[col].split() if num])
        for num in numbers:
            X[i, num] += 1.0
            
    alpha, alpha_0 = estimate_dirichlet_multinomial(X)
    n_j = np.sum(X, axis=0)
    sum_n = np.sum(n_j)
    
    M = 27
    expected_counts = M * (alpha + n_j) / (alpha_0 + sum_n)
    return expected_counts, alpha_0

def main():
    db_path = os.path.join(os.path.dirname(__file__), "xsmb_results.db")
    try:
        expected_counts, alpha_0 = cdm_prediction(db_path, last_days=30)
        print(f"[INFO] CDM Model parameter alpha_0 estimated: {alpha_0:.4f}")
        
        top10 = np.argsort(expected_counts)[-10:][::-1]
        print("\n=========================================")
        print("BAYESIAN CDM MODEL PREDICTION RESULTS:")
        print("Top 10 most potential numbers:")
        for rank, num in enumerate(top10):
            print(f"  Top {rank+1}: {num:02d} (Expected count: {expected_counts[num]:.4f})")
        print("=========================================")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
