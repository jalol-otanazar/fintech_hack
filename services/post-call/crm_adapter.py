"""services/post-call/crm_adapter.py — Pluggable CRM adapter."""
import hashlib, json, os
from datetime import datetime
from pathlib import Path
from shared.types.models import CallSummary, CustomerProfile


class MockCRMAdapter:
    """Always succeeds — used for demo and testing."""

    _PRODUCT_POOL = ["credit_card", "deposit", "student_card", "premium_deposit", "premium_card"]

    def push_summary(self, call_id: str, summary: CallSummary) -> bool:
        print(f"[MockCRM] push_summary call_id={call_id} outcome={summary.outcome}")
        return True

    def fetch_profile(self, customer_id: str) -> CustomerProfile:
        seed = int(hashlib.sha256(customer_id.encode()).hexdigest(), 16)
        age = 18 + (seed % 58)
        income_idx = (seed >> 8) % 10
        income_bracket = "high" if income_idx >= 8 else ("mid" if income_idx >= 4 else "low")
        num_owned = (seed >> 16) % 4
        owned_products = []
        for i in range(num_owned):
            p = self._PRODUCT_POOL[(seed >> (20 + i * 4)) % len(self._PRODUCT_POOL)]
            if p not in owned_products:
                owned_products.append(p)
        txn_raw = (seed >> 32) % 100
        transaction_volume_monthly = float(200_000 + txn_raw * 498_000)
        num_rej = (seed >> 48) % 3
        previous_rejections = [
            self._PRODUCT_POOL[(seed >> (52 + i * 4)) % len(self._PRODUCT_POOL)]
            for i in range(num_rej)
        ]
        tier_idx = (seed >> 60) % 10
        risk_tier = "vip" if tier_idx == 9 else ("premium" if tier_idx >= 6 else "standard")
        return CustomerProfile(
            customer_id=customer_id, age=age, income_bracket=income_bracket,
            owned_products=owned_products, transaction_volume_monthly=transaction_volume_monthly,
            previous_rejections=previous_rejections, risk_tier=risk_tier,
        )


class ConfigDrivenCRMAdapter:
    """
    Maps CallSummary fields to the bank's ABS field names via config/crm_mapping.json.
    Safe to retry (call_id is idempotent key).
    """
    def __init__(self, base_url: str, api_key: str, mapping_path: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers  = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        mapping_file  = mapping_path or Path(__file__).parents[2] / "config/crm_mapping.json"
        with open(mapping_file) as f:
            self.mapping: dict = json.load(f)

    def _map(self, summary: CallSummary) -> dict:
        data = summary.dict()
        return {self.mapping.get(k, k): v for k, v in data.items() if k in self.mapping}

    def push_summary(self, call_id: str, summary: CallSummary) -> bool:
        import httpx
        payload = self._map(summary)
        payload[self.mapping.get("call_id", "call_id")] = call_id
        try:
            r = httpx.post(f"{self.base_url}/calls", json=payload, headers=self.headers, timeout=10)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"[CRM] push failed: {e}")
            return False

    def fetch_profile(self, customer_id: str) -> CustomerProfile | None:
        import httpx
        try:
            r = httpx.get(
                f"{self.base_url}/customers/{customer_id}",
                headers=self.headers,
                timeout=5,
            )
            r.raise_for_status()
            return CustomerProfile(**r.json())
        except Exception as e:
            print(f"[CRM] fetch_profile failed for {customer_id}: {e}")
            return None


def get_adapter():
    crm_url = os.getenv("CRM_URL")
    crm_key = os.getenv("CRM_API_KEY")
    if crm_url and crm_key:
        return ConfigDrivenCRMAdapter(crm_url, crm_key)
    return MockCRMAdapter()
