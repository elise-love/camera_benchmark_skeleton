# 照片與參數對比報告

> 產生來源：`data/<User>/<session>/summary.json`、`raw/`、`processed/`。

## 讀這份報告前先注意

- 目前這批 session 沒有找到 `history.jsonl`，因此無法可靠還原每一張照片拍攝當下的完整候選參數與各項分數。
- 下方的 `最佳參數` 是該 session 最後由 Optuna 選出的 session-level best params，不代表每一張 raw/processed row 都使用同一組參數。
- 每張照片仍有 raw 與 processed 成對列出，方便做視覺比較；若之後補回 `history.jsonl`，這份報告格式可以直接擴充到 per-shot 參數。

## 總覽

- Sessions：5
- Raw / Processed 成對照片：48
- 找到 per-shot history 的 sessions：0

| User | Session | Shots | Best Score | Trials | Summary |
|---|---|---:|---:|---:|---|
| User 3 | `20260728_123052` | 10 | 0.5459 | 10 | [summary.json](../data/User%203/20260728_123052/summary.json) |
| User 4 | `20260728_123852` | 8 | 0.5867 | 8 | [summary.json](../data/User%204/20260728_123852/summary.json) |
| User 5 | `20260728_125149` | 10 | 0.5227 | 10 | [summary.json](../data/User%205/20260728_125149/summary.json) |
| User 6 | `20260728_125959` | 10 | 0.5267 | 10 | [summary.json](../data/User%206/20260728_125959/summary.json) |
| User 7 | `20260728_130809` | 10 | 0.5294 | 10 | [summary.json](../data/User%207/20260728_130809/summary.json) |

## User 3 / 20260728_123052

### 最佳參數（session-level）

| 類別 | 參數 | 數值 |
|---|---|---:|
| 相機 Capture | `Auto Exposure` | 0.75 |
| 相機 Capture | `Exposure` | 9 |
| 相機 Capture | `Auto WB` | 1 |
| 相機 Capture | `White Balance` | 5990.5036 |
| 後製 Processed | `Brightness` | -4.5807 |
| 後製 Processed | `Contrast` | 1.398 |
| 後製 Processed | `Saturation` | 1.4041 |
| 後製 Processed | `Hue Shift` | 0 |
| 後製 Processed | `Gamma` | 1.5898 |
| 後製 Processed | `Temperature` | -2.4965 |
| 後製 Processed | `Filter Enum` | none |

### Raw vs Processed

| Shot | Raw | Processed | 當拍參數 / 分數 |
|---:|---|---|---|
| 1 | [01_raw.png](../data/User%203/20260728_123052/raw/01_raw.png) | [01_processed.png](../data/User%203/20260728_123052/processed/01_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 2 | [02_raw.png](../data/User%203/20260728_123052/raw/02_raw.png) | [02_processed.png](../data/User%203/20260728_123052/processed/02_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 3 | [03_raw.png](../data/User%203/20260728_123052/raw/03_raw.png) | [03_processed.png](../data/User%203/20260728_123052/processed/03_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 4 | [04_raw.png](../data/User%203/20260728_123052/raw/04_raw.png) | [04_processed.png](../data/User%203/20260728_123052/processed/04_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 5 | [05_raw.png](../data/User%203/20260728_123052/raw/05_raw.png) | [05_processed.png](../data/User%203/20260728_123052/processed/05_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 6 | [06_raw.png](../data/User%203/20260728_123052/raw/06_raw.png) | [06_processed.png](../data/User%203/20260728_123052/processed/06_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 7 | [07_raw.png](../data/User%203/20260728_123052/raw/07_raw.png) | [07_processed.png](../data/User%203/20260728_123052/processed/07_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 8 | [08_raw.png](../data/User%203/20260728_123052/raw/08_raw.png) | [08_processed.png](../data/User%203/20260728_123052/processed/08_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 9 | [09_raw.png](../data/User%203/20260728_123052/raw/09_raw.png) | [09_processed.png](../data/User%203/20260728_123052/processed/09_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 10 | [10_raw.png](../data/User%203/20260728_123052/raw/10_raw.png) | [10_processed.png](../data/User%203/20260728_123052/processed/10_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |

## User 4 / 20260728_123852

### 最佳參數（session-level）

| 類別 | 參數 | 數值 |
|---|---|---:|
| 相機 Capture | `Auto Exposure` | 0.75 |
| 相機 Capture | `Exposure` | 9 |
| 相機 Capture | `Auto WB` | 1 |
| 相機 Capture | `White Balance` | 5990.5036 |
| 後製 Processed | `Brightness` | -4.5807 |
| 後製 Processed | `Contrast` | 1.398 |
| 後製 Processed | `Saturation` | 1.4041 |
| 後製 Processed | `Hue Shift` | 0 |
| 後製 Processed | `Gamma` | 1.5898 |
| 後製 Processed | `Temperature` | -2.4965 |
| 後製 Processed | `Filter Enum` | none |

### Raw vs Processed

| Shot | Raw | Processed | 當拍參數 / 分數 |
|---:|---|---|---|
| 1 | [01_raw.png](../data/User%204/20260728_123852/raw/01_raw.png) | [01_processed.png](../data/User%204/20260728_123852/processed/01_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 2 | [02_raw.png](../data/User%204/20260728_123852/raw/02_raw.png) | [02_processed.png](../data/User%204/20260728_123852/processed/02_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 3 | [03_raw.png](../data/User%204/20260728_123852/raw/03_raw.png) | [03_processed.png](../data/User%204/20260728_123852/processed/03_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 4 | [04_raw.png](../data/User%204/20260728_123852/raw/04_raw.png) | [04_processed.png](../data/User%204/20260728_123852/processed/04_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 5 | [05_raw.png](../data/User%204/20260728_123852/raw/05_raw.png) | [05_processed.png](../data/User%204/20260728_123852/processed/05_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 6 | [06_raw.png](../data/User%204/20260728_123852/raw/06_raw.png) | [06_processed.png](../data/User%204/20260728_123852/processed/06_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 7 | [07_raw.png](../data/User%204/20260728_123852/raw/07_raw.png) | [07_processed.png](../data/User%204/20260728_123852/processed/07_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 8 | [08_raw.png](../data/User%204/20260728_123852/raw/08_raw.png) | [08_processed.png](../data/User%204/20260728_123852/processed/08_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |

## User 5 / 20260728_125149

### 最佳參數（session-level）

| 類別 | 參數 | 數值 |
|---|---|---:|
| 相機 Capture | `Auto Exposure` | 0.75 |
| 相機 Capture | `Exposure` | 14 |
| 相機 Capture | `Auto WB` | 1 |
| 相機 Capture | `White Balance` | 7307.4126 |
| 後製 Processed | `Brightness` | 1.7337 |
| 後製 Processed | `Contrast` | 1.2657 |
| 後製 Processed | `Saturation` | 1.0752 |
| 後製 Processed | `Hue Shift` | 0 |
| 後製 Processed | `Gamma` | 2.0835 |
| 後製 Processed | `Temperature` | 17.0239 |
| 後製 Processed | `Filter Enum` | none |

### Raw vs Processed

| Shot | Raw | Processed | 當拍參數 / 分數 |
|---:|---|---|---|
| 1 | [01_raw.png](../data/User%205/20260728_125149/raw/01_raw.png) | [01_processed.png](../data/User%205/20260728_125149/processed/01_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 2 | [02_raw.png](../data/User%205/20260728_125149/raw/02_raw.png) | [02_processed.png](../data/User%205/20260728_125149/processed/02_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 3 | [03_raw.png](../data/User%205/20260728_125149/raw/03_raw.png) | [03_processed.png](../data/User%205/20260728_125149/processed/03_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 4 | [04_raw.png](../data/User%205/20260728_125149/raw/04_raw.png) | [04_processed.png](../data/User%205/20260728_125149/processed/04_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 5 | [05_raw.png](../data/User%205/20260728_125149/raw/05_raw.png) | [05_processed.png](../data/User%205/20260728_125149/processed/05_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 6 | [06_raw.png](../data/User%205/20260728_125149/raw/06_raw.png) | [06_processed.png](../data/User%205/20260728_125149/processed/06_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 7 | [07_raw.png](../data/User%205/20260728_125149/raw/07_raw.png) | [07_processed.png](../data/User%205/20260728_125149/processed/07_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 8 | [08_raw.png](../data/User%205/20260728_125149/raw/08_raw.png) | [08_processed.png](../data/User%205/20260728_125149/processed/08_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 9 | [09_raw.png](../data/User%205/20260728_125149/raw/09_raw.png) | [09_processed.png](../data/User%205/20260728_125149/processed/09_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 10 | [10_raw.png](../data/User%205/20260728_125149/raw/10_raw.png) | [10_processed.png](../data/User%205/20260728_125149/processed/10_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |

## User 6 / 20260728_125959

### 最佳參數（session-level）

| 類別 | 參數 | 數值 |
|---|---|---:|
| 相機 Capture | `Auto Exposure` | 0.75 |
| 相機 Capture | `Exposure` | 9 |
| 相機 Capture | `Auto WB` | 1 |
| 相機 Capture | `White Balance` | 5990.5036 |
| 後製 Processed | `Brightness` | -4.5807 |
| 後製 Processed | `Contrast` | 1.398 |
| 後製 Processed | `Saturation` | 1.4041 |
| 後製 Processed | `Hue Shift` | 0 |
| 後製 Processed | `Gamma` | 1.5898 |
| 後製 Processed | `Temperature` | -2.4965 |
| 後製 Processed | `Filter Enum` | none |

### Raw vs Processed

| Shot | Raw | Processed | 當拍參數 / 分數 |
|---:|---|---|---|
| 1 | [01_raw.png](../data/User%206/20260728_125959/raw/01_raw.png) | [01_processed.png](../data/User%206/20260728_125959/processed/01_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 2 | [02_raw.png](../data/User%206/20260728_125959/raw/02_raw.png) | [02_processed.png](../data/User%206/20260728_125959/processed/02_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 3 | [03_raw.png](../data/User%206/20260728_125959/raw/03_raw.png) | [03_processed.png](../data/User%206/20260728_125959/processed/03_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 4 | [04_raw.png](../data/User%206/20260728_125959/raw/04_raw.png) | [04_processed.png](../data/User%206/20260728_125959/processed/04_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 5 | [05_raw.png](../data/User%206/20260728_125959/raw/05_raw.png) | [05_processed.png](../data/User%206/20260728_125959/processed/05_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 6 | [06_raw.png](../data/User%206/20260728_125959/raw/06_raw.png) | [06_processed.png](../data/User%206/20260728_125959/processed/06_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 7 | [07_raw.png](../data/User%206/20260728_125959/raw/07_raw.png) | [07_processed.png](../data/User%206/20260728_125959/processed/07_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 8 | [08_raw.png](../data/User%206/20260728_125959/raw/08_raw.png) | [08_processed.png](../data/User%206/20260728_125959/processed/08_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 9 | [09_raw.png](../data/User%206/20260728_125959/raw/09_raw.png) | [09_processed.png](../data/User%206/20260728_125959/processed/09_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 10 | [10_raw.png](../data/User%206/20260728_125959/raw/10_raw.png) | [10_processed.png](../data/User%206/20260728_125959/processed/10_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |

## User 7 / 20260728_130809

### 最佳參數（session-level）

| 類別 | 參數 | 數值 |
|---|---|---:|
| 相機 Capture | `Auto Exposure` | 0.75 |
| 相機 Capture | `Exposure` | 9 |
| 相機 Capture | `Auto WB` | 1 |
| 相機 Capture | `White Balance` | 5990.5036 |
| 後製 Processed | `Brightness` | -4.5807 |
| 後製 Processed | `Contrast` | 1.398 |
| 後製 Processed | `Saturation` | 1.4041 |
| 後製 Processed | `Hue Shift` | 0 |
| 後製 Processed | `Gamma` | 1.5898 |
| 後製 Processed | `Temperature` | -2.4965 |
| 後製 Processed | `Filter Enum` | none |

### Raw vs Processed

| Shot | Raw | Processed | 當拍參數 / 分數 |
|---:|---|---|---|
| 1 | [01_raw.png](../data/User%207/20260728_130809/raw/01_raw.png) | [01_processed.png](../data/User%207/20260728_130809/processed/01_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 2 | [02_raw.png](../data/User%207/20260728_130809/raw/02_raw.png) | [02_processed.png](../data/User%207/20260728_130809/processed/02_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 3 | [03_raw.png](../data/User%207/20260728_130809/raw/03_raw.png) | [03_processed.png](../data/User%207/20260728_130809/processed/03_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 4 | [04_raw.png](../data/User%207/20260728_130809/raw/04_raw.png) | [04_processed.png](../data/User%207/20260728_130809/processed/04_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 5 | [05_raw.png](../data/User%207/20260728_130809/raw/05_raw.png) | [05_processed.png](../data/User%207/20260728_130809/processed/05_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 6 | [06_raw.png](../data/User%207/20260728_130809/raw/06_raw.png) | [06_processed.png](../data/User%207/20260728_130809/processed/06_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 7 | [07_raw.png](../data/User%207/20260728_130809/raw/07_raw.png) | [07_processed.png](../data/User%207/20260728_130809/processed/07_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 8 | [08_raw.png](../data/User%207/20260728_130809/raw/08_raw.png) | [08_processed.png](../data/User%207/20260728_130809/processed/08_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 9 | [09_raw.png](../data/User%207/20260728_130809/raw/09_raw.png) | [09_processed.png](../data/User%207/20260728_130809/processed/09_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
| 10 | [10_raw.png](../data/User%207/20260728_130809/raw/10_raw.png) | [10_processed.png](../data/User%207/20260728_130809/processed/10_processed.png) | 目前缺 `history.jsonl`，無法還原當拍參數 |
