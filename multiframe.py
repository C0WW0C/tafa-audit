"""Independent multi-timeframe historical validation on real OHLCV datasets.

Each timeframe is replayed independently with the same paper capital. Results are
reported side by side and are deliberately not summed: the trades overlap in time.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from backtesting.historical import BacktestConfig, HistoricalBacktester


@dataclass(frozen=True)
class MultiTimeframeConfig:
    capital: float = 500.0
    bars: int = 2000
    timeframes: tuple[str, ...] = ("5m", "15m", "1H", "4H")
    symbol: str = "BTC-USDC"
    fee_bps: float = 8.0
    pos_frac: float = 0.15
    atr_sl: float = 2.0
    atr_tp: float = 3.5
    target_tp_pct: float | None = 1.8
    net_target_usd: float | None = 5.0

    def __post_init__(self) -> None:
        if self.capital <= 0:
            raise ValueError("capital must be positive")
        if self.bars < 200:
            raise ValueError("bars must be at least 200")
        if not self.timeframes:
            raise ValueError("at least one timeframe is required")
        if self.target_tp_pct is not None and self.target_tp_pct <= 0:
            raise ValueError("target_tp_pct must be positive")
        if self.net_target_usd is not None and self.net_target_usd <= 0:
            raise ValueError("net_target_usd must be positive")


@dataclass
class MultiTimeframeResult:
    capital_per_timeframe: float
    bars_requested: int
    symbol: str
    results: dict[str, dict] = field(default_factory=dict)
    dataset_manifest: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class MultiTimeframeBacktester:
    """Run isolated historical replays and retain an auditable dataset manifest."""

    def __init__(self, config: MultiTimeframeConfig | None = None) -> None:
        self.config = config or MultiTimeframeConfig()

    def _load_dataset(self, path: str | Path, timeframe: str) -> list[dict]:
        candles = HistoricalBacktester.load_candles(path, timeframe=timeframe)
        if len(candles) < self.config.bars:
            raise ValueError(
                f"{timeframe}: {len(candles)} candles found; {self.config.bars} required"
            )
        selected = candles[-self.config.bars :]
        if len(selected) != self.config.bars:
            raise ValueError(f"{timeframe}: unable to select requested candle window")
        return selected

    def run_files(self, files: dict[str, str | Path]) -> MultiTimeframeResult:
        missing = [tf for tf in self.config.timeframes if tf not in files]
        if missing:
            raise ValueError(f"missing timeframe datasets: {', '.join(missing)}")

        output = MultiTimeframeResult(
            capital_per_timeframe=self.config.capital,
            bars_requested=self.config.bars,
            symbol=self.config.symbol,
        )
        for timeframe in self.config.timeframes:
            source = Path(files[timeframe])
            candles = self._load_dataset(source, timeframe)
            backtest = HistoricalBacktester(
                BacktestConfig(
                    capital=self.config.capital,
                    pos_frac=self.config.pos_frac,
                    fee_bps=self.config.fee_bps,
                    atr_sl=self.config.atr_sl,
                    atr_tp=self.config.atr_tp,
                    symbol=self.config.symbol,
                    target_tp_pct=self.config.target_tp_pct,
                    net_target_usd=self.config.net_target_usd,
                )
            )
            result = backtest.run(candles).to_dict(include_curve=False)
            result["timeframe"] = timeframe
            result["bars"] = len(candles)
            output.results[timeframe] = result
            output.dataset_manifest[timeframe] = {
                "path": str(source),
                "bars": len(candles),
                "from": candles[0].get("ts") or candles[0].get("timestamp"),
                "to": candles[-1].get("ts") or candles[-1].get("timestamp"),
                "source": candles[0].get("source", ""),
            }
        return output

    @staticmethod
    def save_report(result: MultiTimeframeResult, output: str | Path) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return path


def parse_timeframes(value: str | Iterable[str]) -> tuple[str, ...]:
    raw = value.split(",") if isinstance(value, str) else value
    result = tuple(item.strip() for item in raw if item.strip())
    if not result:
        raise ValueError("no timeframes selected")
    return result
