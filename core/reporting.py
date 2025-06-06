"""
Reporting module for the indexfund package.
Contains functions for reporting results and generating performance plots.
"""

# Import from json module
import json

# Import from numpy module
import numpy as np

# Import from metrics module
from core.metrics import calculate_benchmark_performance

# Import from strategy module
from core.strategy import format_strategy_name

# Import from visualization module
from visualization.visualization import (
    plot_metrics_only,
    plot_performance_only,
    print_performance_metrics,
)


def print_strategy_metrics(
    method,
    freq,
    apply_staking,
    stablecoin_allocation,
    start_date,
    initial_investment,
    investment_value,
    prices,
    metrics,
):
    """
    Print performance metrics for a strategy.

    Args:
        method (str): Weighting method
        freq (str): Rebalancing frequency
        apply_staking (bool): Whether staking is applied
        stablecoin_allocation (float): Stablecoin allocation (0.0-1.0)
        start_date (str or datetime): Optional start date
        initial_investment (float): Initial investment amount
        investment_value (list): Investment values over time
        prices (list): Prices over time
        metrics (dict): Performance metrics
    """
    strategy_name = format_strategy_name(
        method, freq, apply_staking, stablecoin_allocation, start_date
    )

    # Print performance metrics
    print_performance_metrics(
        strategy_name, initial_investment, investment_value[-1], prices, metrics
    )


def print_benchmark_metrics(historical_data, initial_investment, start_date=None):
    """
    Print benchmark metrics.

    Args:
        historical_data (dict): Historical data dictionary
        initial_investment (float): Initial investment amount
        start_date (str or datetime, optional): Start date
    """
    if "btc" not in historical_data:
        return

    btc_prices = historical_data["btc"]
    if not btc_prices:
        print("No BTC benchmark data available for the selected time period.")
        return

    btc_investment, btc_metrics = calculate_benchmark_performance(
        btc_prices, initial_investment
    )

    # Print BTC benchmark performance
    btc_values = [price for _, price, _ in btc_prices]
    benchmark_name = "BTC Benchmark"

    if start_date:
        if isinstance(start_date, str):
            start_date_str = start_date
        else:
            start_date_str = start_date.strftime("%Y-%m-%d")
        benchmark_name = f"{benchmark_name} - Start: {start_date_str}"

    print_performance_metrics(
        benchmark_name,
        initial_investment,
        btc_investment[-1],
        btc_values,
        btc_metrics,
    )


def generate_performance_plots(all_performance_data, start_date=None):
    """
    Generate performance comparison plots.

    Args:
        all_performance_data (dict): Dictionary of performance data
        start_date (str or datetime, optional): Start date
    """
    if not all_performance_data:
        return

    # Generate base filename
    base_filename = "strategy_comparison"
    if start_date:
        if isinstance(start_date, str):
            start_date_str = start_date
        else:
            start_date_str = start_date.strftime("%Y-%m-%d")
        base_filename = f"{base_filename}_{start_date_str.replace('-', '')}"

    # Generate performance-only plot without risk metrics
    performance_only_filename = f"pics/performance_only_{base_filename}.png"
    print(f"Generating performance-only plot: {performance_only_filename}")
    plot_performance_only(all_performance_data, output_file=performance_only_filename)

    # Generate metrics-only plot without performance chart
    metrics_only_filename = f"pics/metrics_only_{base_filename}.png"
    print(f"Generating metrics-only comparison plot: {metrics_only_filename}")
    plot_metrics_only(all_performance_data, output_file=metrics_only_filename)


def dump_performance_data_to_json(
    all_performance_data, output_file="performance_data.json"
):
    """
    Dump performance data to a JSON file for frontend visualization.

    Args:
        all_performance_data (dict): Dictionary containing performance data for each strategy
        output_file (str): Path to the output JSON file
    """

    # Convert numpy types to Python native types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        return obj

    # Convert the data
    json_data = convert_numpy_types(all_performance_data)

    # Write to file
    with open(output_file, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"Performance data dumped to: {output_file}")
