import time
from dataclasses import dataclass, field
from typing import List

# Pricing per 1M tokens for openai.gpt-oss-20b (Mumbai region)
INPUT_PRICE_PER_M = 0.08
OUTPUT_PRICE_PER_M = 0.35

@dataclass
class CallMetrics:
    iteration: int
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    ttft_sec: float = 0.0
    total_latency_sec: float = 0.0
    tokens_per_sec: float = 0.0
    cost_usd: float = 0.0

class TelemetryMonitor:
    def __init__(self):
        self.calls: List[CallMetrics] = []

    def record_call(self, iteration: int, input_tokens: int, output_tokens: int, 
                    start_time: float, first_token_time: float, end_time: float) -> CallMetrics:
        
        total_latency = max(end_time - start_time, 0.001)
        ttft = max(first_token_time - start_time, 0.0) if first_token_time else 0.0
        
        # Pure generation duration excludes waiting time for the first token
        gen_duration = max(end_time - first_token_time, 0.001) if first_token_time else total_latency
        tps = output_tokens / gen_duration

        cost = (input_tokens * (INPUT_PRICE_PER_M / 1_000_000)) + \
               (output_tokens * (OUTPUT_PRICE_PER_M / 1_000_000))

        metric = CallMetrics(
            iteration=iteration,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            ttft_sec=round(ttft, 3),
            total_latency_sec=round(total_latency, 3),
            tokens_per_sec=round(tps, 2),
            cost_usd=round(cost, 6)
        )
        self.calls.append(metric)
        return metric

    def print_call_summary(self, m: CallMetrics):
        print(f"\033[94m┌── [METRICS - Iteration {m.iteration}] " + "─" * 38)
        print(f"│ Tokens:     In: {m.input_tokens} | Out: {m.output_tokens} | Total: {m.total_tokens}")
        print(f"│ Latency:    TTFT: {m.ttft_sec}s | Total: {m.total_latency_sec}s | Speed: {m.tokens_per_sec} tok/s")
        print(f"│ Est. Cost:  ${m.cost_usd:.6f}")
        print(f"\033[94m└" + "─" * 60 + "\033[0m")

    def print_session_summary(self):
        if not self.calls:
            return
        total_in = sum(c.input_tokens for c in self.calls)
        total_out = sum(c.output_tokens for c in self.calls)
        total_cost = sum(c.cost_usd for c in self.calls)
        avg_speed = sum(c.tokens_per_sec for c in self.calls) / len(self.calls)
        avg_ttft = sum(c.ttft_sec for c in self.calls) / len(self.calls)

        print(f"\n\033[92m{'=' * 20} SESSION TELEMETRY SUMMARY {'=' * 20}")
        print(f" Total API Calls:        {len(self.calls)}")
        print(f" Total Tokens Consumed:  {total_in + total_out:,} (In: {total_in:,} | Out: {total_out:,})")
        print(f" Average TTFT:           {avg_ttft:.3f}s")
        print(f" Average Speed:          {avg_speed:.2f} tok/s")
        print(f" Total Cost:             ${total_cost:.6f}")
        print(f"{'=' * 67}\033[0m\n")

# Global singleton instance
monitor = TelemetryMonitor()