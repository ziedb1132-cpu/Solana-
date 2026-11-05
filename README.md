# Zied Solana AI

A SOL/USDT-only research and paper-signal engine. This project is separate from Zied Quant and other strategy labs.

## Mission

- Analyze SOL/USDT spot market data.
- Generate BUY or WAIT paper signals; never place live orders.
- Track each open signal until TP, SL, trailing-stop, or time-based exit.
- Record closed outcomes and use eligible outcomes for incremental model training.
- Incorporate Solana-related news published within the previous 24 hours, with publication-time safeguards and duplicate filtering.
- Publish a lightweight HTML dashboard backed by one generated JSON summary file.

## Planned model

- Deep-learning architecture with 30 trainable layers.
- A feature pipeline targeting 1,000+ distinct, validated features across price action, candles, indicators, volume/liquidity, order-book data when available, market regime, cross-market context, and news sentiment/relevance/recency.
- Persist model checkpoints, feature schema, signal history, and training counters between workflow cycles.
- Evaluate chronologically with walk-forward validation, realistic fees/slippage, and leakage prevention. Feature count and depth are design targets, not guarantees of predictive performance.

## Signal lifecycle

`ANALYZE → WAIT or BUY → OPEN → TP / SL / TRAILING / TIME_OUT → CLOSED → LABEL → TRAIN → NEXT CYCLE`

Only one active SOL/USDT paper signal at a time by default. A new signal may be created after the previous one closes. Open signals are not used as closed-outcome labels.

## Dashboard

The dashboard will report current SOL price, latest decision, active and recent signals, exit classifications, net outcomes, news intelligence, model status, feature count, training progress, and validation metrics. The dashboard data export is intended to remain a single JSON file.

## Safety and limitations

- Paper trading only; no exchange credentials or live order execution.
- News and market data are external inputs and may be delayed, incomplete, or incorrect.
- Historical or simulated performance does not guarantee future results.
- The 30-layer / 1,000+ feature design must be validated against data volume and compute limits before enabling model-driven BUY signals.

## Initial implementation status

Project documentation initialized. The data pipeline, signal lifecycle, persistent state, model training, news ingestion, workflow, and dashboard are to be implemented and tested in subsequent commits.
