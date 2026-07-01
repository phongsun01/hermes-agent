"""
XSMB LSTM Research Pipeline
============================
Nghiên cứu dự đoán chuỗi số xổ số bằng LSTM.
⚠️  MỤC ĐÍCH NGHIÊN CỨU / HỌC THUẬT — không đảm bảo độ chính xác thực tế.

Pipeline:
  1. Sinh dữ liệu giả lập (hoặc load CSV thực)
  2. Feature engineering: one-hot, sliding window
  3. Train LSTM multi-output
  4. Đánh giá: top-K accuracy, calibration
  5. Xuất báo cáo + biểu đồ
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import Counter
import json, os, random
from datetime import datetime, timedelta

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Device: {DEVICE}")

# ─────────────────────────────────────────
# 1. DATA LAYER
# ─────────────────────────────────────────

def generate_simulated_xsmb(n_days: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Sinh dữ liệu giả lập XSMB.
    Mỗi ngày có 27 giải → lấy 2 chữ số cuối (lô) → 18 con số 00-99.
    Để giống thực tế hơn: thêm bias nhẹ theo ngày trong tuần.
    """
    rng = np.random.default_rng(seed)
    records = []
    base_date = datetime(2022, 1, 1)

    for i in range(n_days):
        date = base_date + timedelta(days=i)
        dow = date.weekday()          # 0=Mon … 6=Sun
        # Bias nhẹ: cuối tuần có xu hướng số chẵn cao hơn (giả lập)
        weights = np.ones(100)
        if dow >= 5:
            weights[::2] *= 1.05     # số chẵn +5%
        weights /= weights.sum()
        
        lo_set = rng.choice(100, size=18, replace=False, p=weights)
        row = {"date": date.strftime("%Y-%m-%d"), "dow": dow}
        for j, v in enumerate(sorted(lo_set)):
            row[f"lo_{j:02d}"] = v
        records.append(row)

    return pd.DataFrame(records)


def load_or_generate(csv_path: str | None = None) -> pd.DataFrame:
    """Load CSV thực hoặc fallback sang dữ liệu giả lập."""
    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"[DATA] Loaded {len(df)} rows from {csv_path}")
    else:
        print("[DATA] Generating simulated XSMB data (1000 days)...")
        df = generate_simulated_xsmb(1000)
    return df


# ─────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────

LO_COLS = [f"lo_{i:02d}" for i in range(18)]

def build_presence_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    Chuyển mỗi ngày → vector 100 chiều (presence vector).
    presence[i][n] = 1 nếu số n xuất hiện ngày i, else 0.
    """
    n = len(df)
    matrix = np.zeros((n, 100), dtype=np.float32)
    for i, row in df.iterrows():
        for col in LO_COLS:
            if col in df.columns:
                v = int(row[col])
                if 0 <= v <= 99:
                    matrix[i, v] = 1.0
    return matrix


def make_sequences(matrix: np.ndarray, window: int = 14):
    """
    Tạo sliding window sequences.
    X: [window ngày trước] → shape (N, window, 100)
    y: [ngày tiếp theo]    → shape (N, 100)
    """
    X, y = [], []
    for i in range(window, len(matrix)):
        X.append(matrix[i - window:i])
        y.append(matrix[i])
    return np.array(X), np.array(y)


# ─────────────────────────────────────────
# 3. DATASET & MODEL
# ─────────────────────────────────────────

class LotteryDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self): return len(self.X)
    def __getitem__(self, idx): return self.X[idx], self.y[idx]


class LotteryLSTM(nn.Module):
    """
    Kiến trúc:
      LSTM (2 lớp, bidirectional) → Attention pooling → FC → Sigmoid
    Output: xác suất mỗi con số 00-99 xuất hiện ngày tiếp theo.
    """
    def __init__(self, input_size=100, hidden_size=128, num_layers=2,
                 dropout=0.3):
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


# ─────────────────────────────────────────
# 4. TRAINING
# ─────────────────────────────────────────

def train(model, loader, optimizer, criterion):
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


@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    total_loss = 0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
        pred = model(X_batch)
        total_loss += criterion(pred, y_batch).item()
    return total_loss / len(loader)


# ─────────────────────────────────────────
# 5. METRICS
# ─────────────────────────────────────────

def top_k_accuracy(model, X_test, y_test, k=10):
    """
    Top-K accuracy: trong K số được predict xác suất cao nhất,
    có bao nhiêu % trùng với số thực ra?
    Baseline ngẫu nhiên: K/100 = 10% với K=10.
    """
    model.eval()
    X_t = torch.tensor(X_test, dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        probs = model(X_t).cpu().numpy()

    hits = []
    for i in range(len(probs)):
        top_k_pred = set(np.argsort(probs[i])[-k:])
        actual = set(np.where(y_test[i] == 1)[0])
        if len(actual) == 0:
            continue
        hit = len(top_k_pred & actual) / len(actual)
        hits.append(hit)
    return np.mean(hits), np.std(hits)


def frequency_baseline(y_train, y_test, k=10):
    """Baseline: luôn chọn K số hay xuất hiện nhất trong train set."""
    freq = y_train.sum(axis=0)
    top_k = set(np.argsort(freq)[-k:])
    hits = []
    for i in range(len(y_test)):
        actual = set(np.where(y_test[i] == 1)[0])
        if len(actual) == 0:
            continue
        hits.append(len(top_k & actual) / len(actual))
    return np.mean(hits)


def random_baseline(y_test, k=10, n_trials=1000):
    """Baseline: chọn K số ngẫu nhiên."""
    hits = []
    for _ in range(n_trials):
        pred = set(random.sample(range(100), k))
        for i in range(len(y_test)):
            actual = set(np.where(y_test[i] == 1)[0])
            if actual:
                hits.append(len(pred & actual) / len(actual))
    return np.mean(hits)


# ─────────────────────────────────────────
# 6. VISUALIZATION
# ─────────────────────────────────────────

def plot_results(train_losses, val_losses, probs_sample, actual_sample,
                 topk_lstm, topk_freq, topk_rand, out_path):
    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor("#0f1117")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    txt_kw = dict(color="white")
    tick_kw = dict(colors="white")

    # ── A: Loss curve
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("#1a1d27")
    ax1.plot(train_losses, label="Train", color="#4fc3f7", lw=1.5)
    ax1.plot(val_losses,   label="Val",   color="#f06292", lw=1.5)
    ax1.set_title("Training Loss (BCE)", **txt_kw)
    ax1.set_xlabel("Epoch", **txt_kw)
    ax1.legend(facecolor="#1a1d27", labelcolor="white")
    ax1.tick_params(colors="white")
    for sp in ax1.spines.values(): sp.set_color("#333")

    # ── B: Probability heatmap (sample ngày đầu test)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor("#1a1d27")
    bar_colors = ["#f06292" if actual_sample[i] == 1 else "#4fc3f7"
                  for i in range(100)]
    ax2.bar(range(100), probs_sample, color=bar_colors, alpha=0.85)
    ax2.set_title("Xác suất dự đoán (đỏ = số thực ra)", **txt_kw)
    ax2.set_xlabel("Số (00–99)", **txt_kw)
    ax2.set_ylabel("Prob", **txt_kw)
    ax2.tick_params(colors="white")
    for sp in ax2.spines.values(): sp.set_color("#333")

    # ── C: Accuracy comparison bar
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor("#1a1d27")
    methods = ["Random\nBaseline", "Frequency\nBaseline", "LSTM\n(ours)"]
    values  = [topk_rand, topk_freq, topk_lstm]
    colors  = ["#78909c", "#ffd54f", "#69f0ae"]
    bars = ax3.bar(methods, [v*100 for v in values], color=colors, width=0.5)
    for bar, v in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f"{v*100:.1f}%", ha="center", va="bottom", color="white", fontsize=11)
    ax3.set_title("Top-10 Accuracy (% số đúng trong top 10 dự đoán)", **txt_kw)
    ax3.set_ylabel("%", **txt_kw)
    ax3.tick_params(colors="white")
    ax3.set_ylim(0, max(values)*100 * 1.25)
    for sp in ax3.spines.values(): sp.set_color("#333")

    # ── D: Annotation / insight
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor("#1a1d27")
    ax4.axis("off")
    insight_lines = [
        "📊  KẾT QUẢ NGHIÊN CỨU",
        "",
        f"  Random baseline:    {topk_rand*100:.1f}%",
        f"  Frequency baseline: {topk_freq*100:.1f}%",
        f"  LSTM model:         {topk_lstm*100:.1f}%",
        "",
        "⚠️  LƯU Ý QUAN TRỌNG:",
        "",
        "  Xổ số vật lý là quá trình ngẫu nhiên",
        "  thực sự (IID). Mọi 'pattern' tìm được",
        "  từ lịch sử đều là ảo giác thống kê.",
        "",
        "  Nếu LSTM > baseline đáng kể trên dữ",
        "  liệu GIẢ LẬP → do data có bias cố ý.",
        "  Trên dữ liệu thực → xấp xỉ baseline.",
        "",
        "  Pipeline này hữu ích để học:",
        "  • LSTM / attention mechanism",
        "  • Time-series ML",
        "  • Thiết kế experiment & baseline",
    ]
    ax4.text(0.05, 0.95, "\n".join(insight_lines),
             transform=ax4.transAxes, va="top", ha="left",
             color="white", fontsize=9.5,
             fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#252836",
                       edgecolor="#444", alpha=0.9))

    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"[PLOT] Saved → {out_path}")


# ─────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────

def run(csv_path=None, window=14, epochs=50, batch_size=32, k=10):
    os.makedirs("/mnt/user-data/outputs", exist_ok=True)

    # Data
    df = load_or_generate(csv_path)
    matrix = build_presence_matrix(df)
    X, y = make_sequences(matrix, window=window)
    print(f"[DATA] Sequences: X={X.shape}, y={y.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, shuffle=False)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.15, shuffle=False)

    train_ds = LotteryDataset(X_train, y_train)
    val_ds   = LotteryDataset(X_val,   y_val)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size)

    # Model
    model = LotteryLSTM().to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=5, factor=0.5)
    criterion = nn.BCELoss()

    # Train
    train_losses, val_losses = [], []
    best_val, best_state = float("inf"), None
    print(f"\n[TRAIN] {epochs} epochs, window={window}, batch={batch_size}")
    for epoch in range(1, epochs + 1):
        tl = train(model, train_loader, optimizer, criterion)
        vl = evaluate(model, val_loader, criterion)
        scheduler.step(vl)
        train_losses.append(tl)
        val_losses.append(vl)
        if vl < best_val:
            best_val = vl
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        if epoch % 10 == 0:
            print(f"  Epoch {epoch:3d}/{epochs} | train={tl:.4f} | val={vl:.4f}")

    model.load_state_dict(best_state)

    # Metrics
    topk_lstm, topk_std = top_k_accuracy(model, X_test, y_test, k=k)
    topk_freq = frequency_baseline(y_train, y_test, k=k)
    topk_rand = random_baseline(y_test, k=k)

    print(f"\n[RESULT] Top-{k} Accuracy:")
    print(f"  Random baseline:    {topk_rand*100:.2f}%")
    print(f"  Frequency baseline: {topk_freq*100:.2f}%")
    print(f"  LSTM (best val):    {topk_lstm*100:.2f}% ± {topk_std*100:.2f}%")

    # Sample prediction (ngày đầu test)
    model.eval()
    sample_X = torch.tensor(X_test[:1], dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        probs_sample = model(sample_X).cpu().numpy()[0]
    top10 = np.argsort(probs_sample)[-10:][::-1]
    actual_today = set(np.where(y_test[0] == 1)[0])
    print(f"\n[PREDICT] Top-10 dự đoán ngày test đầu tiên:")
    print(f"  Predicted: {sorted(top10.tolist())}")
    print(f"  Actual:    {sorted(actual_today)}")
    hits = sorted(set(top10.tolist()) & actual_today)
    print(f"  Trúng:     {hits} ({len(hits)}/{len(actual_today)})")

    # Plot
    out_img = "/mnt/user-data/outputs/xsmb_lstm_research.png"
    plot_results(
        train_losses, val_losses,
        probs_sample, y_test[0],
        topk_lstm, topk_freq, topk_rand,
        out_img
    )

    # Save summary JSON
    summary = {
        "config": {"window": window, "epochs": epochs, "k": k},
        "results": {
            "random_baseline": round(topk_rand, 4),
            "frequency_baseline": round(topk_freq, 4),
            "lstm_topk_acc": round(topk_lstm, 4),
            "lstm_topk_std": round(topk_std, 4),
        },
        "top10_prediction_sample": sorted(top10.tolist()),
        "actual_sample": sorted(list(actual_today)),
        "hits": hits,
    }
    json_path = "/mnt/user-data/outputs/xsmb_lstm_summary.json"
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, np.floating): return float(obj)
            return super().default(obj)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, cls=NpEncoder)
    print(f"[SUMMARY] → {json_path}")

    return model, summary


if __name__ == "__main__":
    model, summary = run(
        csv_path=None,   # Thay bằng path CSV thực nếu có
        window=14,
        epochs=60,
        batch_size=32,
        k=10
    )
