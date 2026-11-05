# Zied Solana AI

A SOL/USDT-only research and paper-signal engine, separate from Zied Quant and other strategy labs.

## Scope

- Analyze SOL/USDT Spot market data and generate BUY/WAIT paper signals only; no live orders.
- Track every BUY signal until TP, SL, or a trailing stop closes it. **There is no time-based exit.** A signal stays open until a price-based exit condition is met.
- Record each closed result and train only on eligible, fully closed outcomes.
- Incorporate Solana-related news published in the previous 24 hours with duplicate filtering and publication-time safeguards.
- Preserve model checkpoints, signal history, feature schema, and learning counters across workflow cycles.

## Model targets

- Deep-learning architecture with 30 trainable layers.
- Feature pipeline targeting 1,000+ distinct, validated features from price action, candles, indicators, volume/liquidity, order-book data when available, market regime, cross-market context, and news sentiment/relevance/recency.
- Chronological walk-forward evaluation with fees/slippage and leakage prevention. Depth and feature count are targets, not guarantees of predictive performance.

## Signal lifecycle

`ANALYZE → WAIT or BUY → OPEN → TP / SL / TRAILING → CLOSED → LABEL → TRAIN → NEXT CYCLE`

Only one active SOL/USDT paper signal at a time by default. A new signal may be created after the previous one closes. Open signals are not used as closed-outcome labels.

## Lightweight dashboard summary

`solana_summary.json` is the small, dashboard-facing summary updated on every completed cycle. It contains only the SOL price, total signal count, TP count, SL count, active signal summary, cycle number, and update timestamp. Detailed training data and full signal history remain separate from this compact file.

The main Zied Quant HTML dashboard can consume this JSON for a dedicated Solana section without downloading the full learning state.

## Safety

- Paper trading only; no exchange credentials or live order execution.
- Market/news data may be delayed, incomplete, or incorrect.
- Simulated performance does not guarantee future results.
- Validate the 30-layer / 1,000+ feature model against data volume and compute limits before relying on its signals.

## Implementation status

Project documentation and the compact summary JSON schema are initialized. Engine, signal manager, news ingestion, persistent learning, workflow, and dashboard integration remain to be implemented and tested.
