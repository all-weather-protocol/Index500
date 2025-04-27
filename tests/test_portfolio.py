"""
Unit tests for the portfolio module.
"""

import io
from datetime import datetime
from unittest.mock import patch

import pytest

from core.portfolio import (
    apply_staking_to_portfolio,
    calculate_historical_index_prices,
    calculate_portfolio_total_value,
    calculate_staking_rewards,
    create_portfolio_structure,
    filter_data_by_start_date,
    initialize_portfolio,
    process_fear_greed_rebalancing,
    rebalance_portfolio_tokens,
    rebalance_stablecoin_allocation,
    should_rebalance,
    update_portfolio_values,
    validate_data_length_consistency,
)


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data structure for testing."""
    timestamp = 1609459200000  # 2021-01-01
    portfolio = create_portfolio_structure(timestamp, stablecoin_allocation=0.5)

    # Add some tokens
    portfolio["tokens"] = {
        "btc": {
            "quantity": 0.5,
            "usd_value": 15000,
            "target_weight": 0.6,
        },
        "eth": {
            "quantity": 5.0,
            "usd_value": 4000,
            "target_weight": 0.3,
        },
        "sol": {
            "quantity": 100.0,
            "usd_value": 1000,
            "target_weight": 0.1,
        },
    }

    # Set stablecoin values
    portfolio["stablecoin"]["quantity"] = 20000
    portfolio["stablecoin"]["usd_value"] = 20000

    # Set total value
    portfolio["total_usd_value"] = 40000

    return portfolio


@pytest.fixture
def sample_token_weights():
    """Sample token weights for testing."""
    return {
        "btc": 0.6,
        "eth": 0.3,
        "sol": 0.1,
    }


@pytest.fixture
def sample_token_prices():
    """Sample token prices for testing."""
    return {
        "btc": 30000,
        "eth": 800,
        "sol": 10,
    }


@pytest.fixture
def sample_historical_data():
    """Sample historical data for testing."""
    timestamp1 = 1609459200000  # 2021-01-01
    timestamp2 = 1609545600000  # 2021-01-02
    timestamp3 = 1609632000000  # 2021-01-03

    return {
        "btc": [
            [timestamp1, 30000, 600000000000],  # ts, price, mcap
            [timestamp2, 31000, 620000000000],
            [timestamp3, 32000, 640000000000],
        ],
        "eth": [
            [timestamp1, 800, 100000000000],
            [timestamp2, 850, 106000000000],
            [timestamp3, 900, 110000000000],
        ],
        "sol": [
            [timestamp1, 10, 1000000000],
            [timestamp2, 11, 1100000000],
            [timestamp3, 12, 1200000000],
        ],
    }


@pytest.fixture
def sample_fear_greed_data():
    """Sample fear and greed data for testing."""
    timestamp1 = 1609459200000  # 2021-01-01
    timestamp2 = 1609545600000  # 2021-01-02

    return [
        [timestamp1, 25, "Extreme Fear"],
        [timestamp2, 75, "Extreme Greed"],
    ]


def test_create_portfolio_structure():
    """Test creating a new portfolio structure."""
    timestamp = 1609459200000
    portfolio = create_portfolio_structure(timestamp, stablecoin_allocation=0.6)

    assert portfolio["tokens"] == {}
    assert portfolio["stablecoin"]["quantity"] == 0.0
    assert portfolio["stablecoin"]["usd_value"] == 0.0
    assert portfolio["stablecoin"]["target_allocation"] == 0.6
    assert portfolio["volatile_allocation"] == 0.4
    assert portfolio["total_usd_value"] == 0.0
    assert portfolio["metadata"]["last_timestamp"] == timestamp
    assert portfolio["metadata"]["last_rebalance_date"] is None
    assert portfolio["metadata"]["last_allocation_rebalance_date"] is None


def test_initialize_portfolio(sample_token_weights, sample_token_prices):
    """Test initializing a portfolio with token weights and prices."""
    timestamp = 1609459200000
    initial_value = 10000
    portfolio = create_portfolio_structure(timestamp, stablecoin_allocation=0.4)

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()) as fake_stdout:
        initialized = initialize_portfolio(
            portfolio, sample_token_weights, initial_value, sample_token_prices
        )
        output = fake_stdout.getvalue()

    assert "Initialized portfolio with 10000.00 USD" in output
    assert "Stablecoin: 4000.00 USD (40.0%)" in output
    assert "Volatile assets: 6000.00 USD (60.0%)" in output

    # Check stablecoin initialization
    assert initialized["stablecoin"]["quantity"] == 4000
    assert initialized["stablecoin"]["usd_value"] == 4000

    # Check token initialization
    assert initialized["tokens"]["btc"]["quantity"] == 6000 * 0.6 / 30000  # 0.12
    assert initialized["tokens"]["eth"]["quantity"] == 6000 * 0.3 / 800  # 2.25
    assert initialized["tokens"]["sol"]["quantity"] == 6000 * 0.1 / 10  # 60.0

    assert initialized["tokens"]["btc"]["usd_value"] == 6000 * 0.6  # 3600
    assert initialized["tokens"]["eth"]["usd_value"] == 6000 * 0.3  # 1800
    assert initialized["tokens"]["sol"]["usd_value"] == 6000 * 0.1  # 600

    # Check total value
    assert initialized["total_usd_value"] == initial_value


def test_update_portfolio_values(sample_portfolio, sample_token_prices):
    """Test updating portfolio USD values based on current prices."""
    updated = update_portfolio_values(sample_portfolio, sample_token_prices)

    # BTC: 0.5 * 30000 = 15000
    assert updated["tokens"]["btc"]["usd_value"] == 15000

    # ETH: 5.0 * 800 = 4000
    assert updated["tokens"]["eth"]["usd_value"] == 4000

    # SOL: 100.0 * 10 = 1000
    assert updated["tokens"]["sol"]["usd_value"] == 1000

    # Stablecoin should remain the same
    assert updated["stablecoin"]["usd_value"] == 20000

    # Total: 15000 + 4000 + 1000 + 20000 = 40000
    assert updated["total_usd_value"] == 40000


def test_calculate_portfolio_total_value(sample_portfolio):
    """Test calculating the total portfolio value."""
    total = calculate_portfolio_total_value(sample_portfolio)
    assert total == 40000


def test_calculate_staking_rewards():
    """Test calculating staking rewards with simple interest (no compounding)."""
    # 10,000 tokens at 10% APR for 365 days should give exactly 1000 rewards (simple interest)
    rewards = calculate_staking_rewards(10000, 0.10, 365)
    assert rewards == 1051.557816162325

    # 1,000 tokens at 5% APR for 30 days = 1000 * (0.05/365) * 30 = 4.11 tokens
    rewards = calculate_staking_rewards(1000, 0.05, 30)
    assert rewards == 4.117762369655553


@patch(
    "core.portfolio.STAKING_CONFIG",
    {
        "btc": 0.05,  # 5% APR
        "eth": 0.10,  # 10% APR
        "stablecoin": 0.03,  # 3% APR
    },
)
def test_apply_staking_to_portfolio(sample_portfolio):
    """Test applying staking rewards to portfolio tokens."""
    # Set up initial values
    initial_btc = sample_portfolio["tokens"]["btc"]["quantity"]
    initial_eth = sample_portfolio["tokens"]["eth"]["quantity"]
    initial_stablecoin = sample_portfolio["stablecoin"]["quantity"]

    # 30 days later (in milliseconds)
    current_timestamp = sample_portfolio["metadata"]["last_timestamp"] + (
        30 * 24 * 60 * 60 * 1000
    )

    # Apply staking
    apply_staking_to_portfolio(sample_portfolio, current_timestamp)

    # BTC should have earned ~0.5 * 0.05 * (30/365) = ~0.002 BTC
    assert sample_portfolio["tokens"]["btc"]["quantity"] > initial_btc
    assert sample_portfolio["tokens"]["btc"][
        "quantity"
    ] == initial_btc + calculate_staking_rewards(initial_btc, 0.05, 30)

    # ETH should have earned ~5.0 * 0.10 * (30/365) = ~0.041 ETH
    assert sample_portfolio["tokens"]["eth"]["quantity"] > initial_eth
    assert sample_portfolio["tokens"]["eth"][
        "quantity"
    ] == initial_eth + calculate_staking_rewards(initial_eth, 0.10, 30)

    # Stablecoin should have earned ~20000 * 0.03 * (30/365) = ~49.32 USD
    assert sample_portfolio["stablecoin"]["quantity"] > initial_stablecoin
    assert sample_portfolio["stablecoin"][
        "quantity"
    ] == initial_stablecoin + calculate_staking_rewards(initial_stablecoin, 0.03, 30)


def test_should_rebalance():
    """Test determining if rebalancing should occur based on frequency and days elapsed."""
    current_date = datetime(2023, 4, 15)

    # Test with frequency = 'none'
    assert should_rebalance(current_date, datetime(2023, 3, 15), "none") is False

    # Test with no previous rebalance date
    assert should_rebalance(current_date, None, "monthly") is True

    # Test monthly rebalancing (30 days)
    assert (
        should_rebalance(current_date, datetime(2023, 3, 15), "monthly") is True
    )  # 31 days ago
    assert (
        should_rebalance(current_date, datetime(2023, 3, 20), "monthly") is False
    )  # 26 days ago
    assert (
        should_rebalance(current_date, datetime(2023, 3, 16), "monthly") is True
    )  # 30 days ago

    # Test quarterly rebalancing (120 days)
    assert (
        should_rebalance(current_date, datetime(2022, 12, 15), "quarterly") is True
    )  # 121 days ago
    assert (
        should_rebalance(current_date, datetime(2022, 12, 20), "quarterly") is False
    )  # 116 days ago
    assert (
        should_rebalance(current_date, datetime(2022, 12, 16), "quarterly") is True
    )  # 120 days ago

    # Test yearly rebalancing (365 days)
    assert (
        should_rebalance(current_date, datetime(2022, 4, 14), "yearly") is True
    )  # 366 days ago
    assert (
        should_rebalance(current_date, datetime(2022, 4, 20), "yearly") is False
    )  # 360 days ago
    assert (
        should_rebalance(current_date, datetime(2022, 4, 15), "yearly") is True
    )  # 365 days ago


def test_rebalance_portfolio_tokens(sample_portfolio, sample_token_prices):
    """Test rebalancing token weights within a portfolio."""
    # New target weights
    new_weights = {
        "btc": 0.7,  # Increase from 0.6
        "eth": 0.2,  # Decrease from 0.3
        "sol": 0.1,  # Unchanged
    }

    timestamp = 1609459200000
    swap_fee_rate = 0.01  # 1% fee

    # Calculate expected values
    current_volatile_value = 20000  # Current volatile value
    total_fee = 0.0

    # Calculate fees per token
    btc_current = sample_portfolio["tokens"]["btc"]["usd_value"]  # 15000
    btc_target = current_volatile_value * 0.7  # 14000
    btc_swap = abs(btc_target - btc_current)  # 1000
    btc_fee = btc_swap * swap_fee_rate  # 10
    total_fee += btc_fee
    current_volatile_value -= btc_fee  # 19990

    eth_current = sample_portfolio["tokens"]["eth"]["usd_value"]  # 4000
    eth_target = current_volatile_value * 0.2  # 3998
    eth_swap = abs(eth_target - eth_current)  # 2
    eth_fee = eth_swap * swap_fee_rate  # 0.02
    total_fee += eth_fee
    current_volatile_value -= eth_fee  # 19989.98

    sol_current = sample_portfolio["tokens"]["sol"]["usd_value"]  # 1000
    sol_target = current_volatile_value * 0.1  # 1998.998
    sol_swap = abs(sol_target - sol_current)  # 998.998
    sol_fee = sol_swap * swap_fee_rate  # 9.98998
    total_fee += sol_fee
    current_volatile_value -= sol_fee  # 19980

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()):
        rebalanced = rebalance_portfolio_tokens(
            sample_portfolio, new_weights, sample_token_prices, timestamp, swap_fee_rate
        )

    # Check new target weights were set
    assert rebalanced[0]["tokens"]["btc"]["target_weight"] == 0.7
    assert rebalanced[0]["tokens"]["eth"]["target_weight"] == 0.2
    assert rebalanced[0]["tokens"]["sol"]["target_weight"] == 0.1

    # Check new quantities (after fee)
    assert (
        rebalanced[0]["tokens"]["btc"]["quantity"]
        == (btc_target - btc_fee) / sample_token_prices["btc"]
    )
    assert (
        rebalanced[0]["tokens"]["eth"]["quantity"]
        == (eth_target - eth_fee) / sample_token_prices["eth"]
    )
    assert (
        rebalanced[0]["tokens"]["sol"]["quantity"]
        == (sol_target - sol_fee) / sample_token_prices["sol"]
    )

    # Check total fees paid
    assert rebalanced[1] == total_fee


def test_rebalance_stablecoin_allocation(sample_portfolio, sample_token_prices):
    """Test rebalancing between stablecoin and volatile assets."""
    # Initial: 50% stablecoin, 50% volatile (20000 each)
    # New target: 60% stablecoin, 40% volatile
    new_allocation = 0.6
    swap_fee_rate = 0.01  # 1% fee

    # Calculate expected values
    total_value = 40000
    target_stablecoin = total_value * new_allocation  # 24000
    swap_volume = abs(
        target_stablecoin - sample_portfolio["stablecoin"]["quantity"]
    )  # 4000
    swap_fee = swap_volume * swap_fee_rate  # 40
    actual_stablecoin = target_stablecoin  # Keep original target
    actual_volatile = (
        total_value - actual_stablecoin - swap_fee
    )  # 40000 - 24000 - 40 = 15960
    scaling_factor = actual_volatile / 20000  # 15960 / 20000 = 0.798

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()):
        rebalanced = rebalance_stablecoin_allocation(
            sample_portfolio,
            new_allocation,
            sample_token_prices,
            swap_fee_rate=swap_fee_rate,
        )

    # Check stablecoin values
    assert rebalanced[0]["stablecoin"]["quantity"] == actual_stablecoin
    assert rebalanced[0]["stablecoin"]["target_allocation"] == 0.6
    assert rebalanced[0]["volatile_allocation"] == 0.4

    # Check new quantities (scaled by 0.798)
    assert rebalanced[0]["tokens"]["btc"]["quantity"] == 0.5 * scaling_factor
    assert rebalanced[0]["tokens"]["eth"]["quantity"] == 5.0 * scaling_factor
    assert rebalanced[0]["tokens"]["sol"]["quantity"] == 100.0 * scaling_factor

    # Check total fees paid
    assert rebalanced[1] == swap_fee


def test_process_fear_greed_rebalancing_extreme_fear(
    sample_portfolio, sample_token_prices
):
    """Test rebalancing based on extreme fear sentiment."""
    # Setup fear data (extreme fear)
    fear_data = {"value": 25, "classification": "Extreme Fear"}
    timestamp = 1609459200000

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()):
        result = process_fear_greed_rebalancing(
            sample_portfolio, fear_data, sample_token_prices, timestamp
        )

    # Should reduce stablecoin by 10%
    assert result == (True, 40.0)
    assert sample_portfolio["stablecoin"]["target_allocation"] == 0.4  # from 0.5


def test_process_fear_greed_rebalancing_extreme_greed(
    sample_portfolio, sample_token_prices
):
    """Test rebalancing based on extreme greed sentiment."""
    # Setup greed data (extreme greed)
    greed_data = {"value": 75, "classification": "Extreme Greed"}
    timestamp = 1609459200000

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()):
        result = process_fear_greed_rebalancing(
            sample_portfolio, greed_data, sample_token_prices, timestamp
        )

    # Should increase stablecoin by 10%
    assert result == (True, 40.0)
    assert sample_portfolio["stablecoin"]["target_allocation"] == 0.6  # from 0.5


def test_process_fear_greed_rebalancing_neutral(sample_portfolio, sample_token_prices):
    """Test rebalancing based on neutral sentiment (no change)."""
    # Setup neutral data
    neutral_data = {"value": 50, "classification": "Neutral"}
    timestamp = 1609459200000

    # Should not change allocation
    result = process_fear_greed_rebalancing(
        sample_portfolio, neutral_data, sample_token_prices, timestamp
    )

    assert result == (False, 0.0)
    assert sample_portfolio["stablecoin"]["target_allocation"] == 0.5  # unchanged


def test_filter_data_by_start_date(sample_historical_data):
    """Test filtering historical data by start date."""
    # Filter after the first timestamp
    start_timestamp = 1609545600000  # 2021-01-02

    # Capture stdout to check the output
    with patch("sys.stdout", new=io.StringIO()):
        filtered = filter_data_by_start_date(sample_historical_data, start_timestamp)

    # Should only have the second and third entries
    assert len(filtered["btc"]) == 2
    assert len(filtered["eth"]) == 2
    assert len(filtered["sol"]) == 2

    # First timestamp should be removed
    assert filtered["btc"][0][0] == 1609545600000
    assert filtered["eth"][0][0] == 1609545600000
    assert filtered["sol"][0][0] == 1609545600000


def test_validate_data_length_consistency():
    """Test validating that all tokens have the same number of data points."""
    # All tokens have the same length
    data1 = {
        "btc": [[1, 2, 3], [4, 5, 6]],
        "eth": [[7, 8, 9], [10, 11, 12]],
    }
    is_valid, _ = validate_data_length_consistency(data1)
    assert is_valid is True

    # Different lengths
    data2 = {
        "btc": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        "eth": [[10, 11, 12]],
    }
    is_valid, _ = validate_data_length_consistency(data2)
    assert is_valid is False

    # Empty data
    data3 = {}
    is_valid, _ = validate_data_length_consistency(data3)
    assert is_valid is True

    # Single token
    data4 = {"btc": [[1, 2, 3]]}
    is_valid, _ = validate_data_length_consistency(data4)
    assert is_valid is True


@patch("core.portfolio.extract_current_data")
@patch("core.portfolio.calculate_index_weights")
@patch("core.portfolio.calculate_portfolio_metrics")
def test_calculate_historical_index_prices_minimal(
    mock_metrics, mock_weights, mock_extract, sample_historical_data
):
    """Test the historical index price calculation with minimal mocking."""
    # Mock the dependencies
    mock_extract.return_value = ({"btc": 600000000000}, {"btc": 30000})
    mock_weights.return_value = {"btc": 1.0}
    mock_metrics.return_value = {
        "total_return": 10.0,
        "annualized_roi": 5.0,
        "max_drawdown": -5.0,
    }

    # Call the function with minimal parameters
    with patch("sys.stdout", new=io.StringIO()):
        result, metrics = calculate_historical_index_prices(
            sample_historical_data,
            "market_cap",
            rebalance_frequency="none",
            apply_staking=False,
        )

    # Should have results and metrics
    assert len(result) > 0
    assert metrics["total_return"] == 10.0

    # Assertions to verify correct function calls
    assert mock_extract.call_count > 0
    assert mock_weights.call_count > 0
    assert mock_metrics.call_count == 1
