# Zied Solana AI

A SOL/USDT-only research and paper-signal engine, separate from Zied Quant and other strategy labs.

## Operating rules

- SOL/USDT Spot analysis only; BUY/WAIT paper signals, no real orders or exchange credentials.
- One active paper signal at a time. A new signal may open only after the previous one closes.
- Signal exits are price-based: TP, SL, or a tightened trailing SL. **No Time Exit.**
- Every signal records its strategy, entry reason, score, timeframe, market regime, feature snapshot, original/current TP and SL, trailing changes, and net result.
- Net results account for configurable simulated fees and slippage (PAPER_FEE_PCT, PAPER_SLIPPAGE_PCT).

## Analysis and strategy discovery

- Stable 1,205-key feature schema: 200 observed candle/return descriptors, five deterministic transformations of those descriptors, and five market/news context values.
- Transformed features are derived from the same market observations; they are not 1,205 independent data sources.
- Multi-timeframe context uses 5m, 15m, 1h, and 4h candles. Order-book imbalance/spread and recent Solana news sentiment are included where available.
- Eight explainable strategy families are discovered and ranked dynamically.
- Historical strategy simulation uses future candles only after each historical entry, conservative SL-first handling when TP and SL are touched in the same candle, and estimated fees/slippage.
- Strategy eligibility currently requires at least 20 completed simulated trades, positive net expectancy, and profit factor above 1.0. Results are research estimates, not guarantees.

## AI learning gate

- The 30-layer neural network remains inactive until the persisted history contains at least 500 net-profitable and 500 net-losing closed outcomes.
- Only fully closed signals are eligible for training.
- After activation, retraining is attempted when at least five additional closed outcomes have accumulated.
- The model's probability filter is applied only when a compatible checkpoint exists. Otherwise, the strategy engine continues in paper mode without pretending the AI is ready.
- Training uses chronological 80/20 separation and records train/validation loss. This is a basic safeguard, not a substitute for robust walk-forward validation.

## Persistence and workflow

- GitHub Actions executes 100 cycles, persists state after each cycle, then dispatches the next workflow run.
- State is never reset by a normal workflow start.
- solana_summary.json is the compact dashboard feed; detailed history remains in solana_state.json.
- When solana_state.json exceeds 90 MiB, state_storage.py splits it into repository parts with a SHA-256 manifest. The next run reconstructs and verifies the original JSON before processing.
- Model checkpoint and top-strategy snapshot are persisted between cycles.
- A workflow concurrency group prevents overlapping engine runs.

## Dashboard

The Solana tab in the main Zied Quant dashboard reads only solana_summary.json and shows current price, signal counts, active signal details, TP/SL/trailing levels, feature count, AI gate, market regime, and the dynamically ranked top 20 strategies.

## Safety and interpretation

All orders and outcomes are simulated. Exchange candles, order-book snapshots, and news feeds can be delayed or incomplete. Strategy backtests and model probabilities can overfit and do not imply future profitability. No model is allowed to control entries before its learning gate is met and a compatible model checkpoint is saved.
