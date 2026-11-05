"""
Tests for restocking order API endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restocking_orders():
    """Restocking orders are module-level state; isolate each test."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


class TestRestockingEndpoints:
    """Test suite for restocking order endpoints."""

    def test_demand_forecasts_include_cost_and_lead_time(self, client):
        """Forecasts expose the pricing data the restocking tab budgets against."""
        response = client.get("/api/demand")
        assert response.status_code == 200
        for forecast in response.json():
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0

    def test_get_restocking_orders_empty(self, client):
        """No orders are returned before any are submitted."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restocking_order(self, client):
        """Totals, lead time and expected delivery are computed server-side."""
        # WDG-001: $12.50, 14 days · FLT-405: $8.75, 5 days
        payload = {
            "budget": 5000,
            "items": [
                {"sku": "WDG-001", "quantity": 100},
                {"sku": "FLT-405", "quantity": 100},
            ],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert order["total_cost"] == 2125.0
        assert order["budget"] == 5000
        assert order["lead_time_days"] == 14  # slowest item wins
        assert len(order["items"]) == 2
        assert order["items"][0]["name"] == "Industrial Widget Type A"
        assert order["items"][0]["line_total"] == 1250.0

        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert expected - submitted == timedelta(days=14)

    def test_create_order_ignores_client_price(self, client):
        """Extra price fields from the client must not affect the total."""
        payload = {"budget": 2000, "items": [{"sku": "WDG-001", "quantity": 100, "unit_cost": 0.01}]}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201
        assert response.json()["total_cost"] == 1250.0

    def test_get_restocking_orders_newest_first(self, client):
        """Submitted orders are listed newest first."""
        for qty in (10, 20):
            client.post("/api/restocking-orders",
                        json={"budget": 1000, "items": [{"sku": "GSK-203", "quantity": qty}]})

        orders = client.get("/api/restocking-orders").json()
        assert len(orders) == 2
        assert orders[0]["items"][0]["quantity"] == 20
        assert orders[0]["order_number"] != orders[1]["order_number"]

    @pytest.mark.parametrize("payload", [
        {"budget": 1000, "items": []},
        {"budget": 1000, "items": [{"sku": "NOPE-999", "quantity": 1}]},
        {"budget": 1000, "items": [{"sku": "WDG-001", "quantity": 0}]},
        {"budget": 1000, "items": [{"sku": "WDG-001", "quantity": -5}]},
        {"budget": 100, "items": [{"sku": "WDG-001", "quantity": 100}]},
    ], ids=["empty", "unknown-sku", "zero-qty", "negative-qty", "over-budget"])
    def test_create_restocking_order_invalid(self, client, payload):
        """Invalid orders are rejected with 400 and not stored."""
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "detail" in response.json()
        assert client.get("/api/restocking-orders").json() == []

    def test_create_restocking_order_missing_fields(self, client):
        """Malformed bodies fail Pydantic validation."""
        response = client.post("/api/restocking-orders", json={"items": []})
        assert response.status_code == 422
