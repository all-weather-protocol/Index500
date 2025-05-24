import numpy as np


def calculate_age_risk(protocol_ages):
    """Calculate risk score based on protocol age using relative values"""
    # Convert to numpy array for vectorized operations
    ages = np.array(protocol_ages)
    # Normalize to 0-1 range where 1 is highest risk (newest protocol)
    max_age = np.max(ages)
    return 1 - (ages / max_age)


def calculate_tvl_risk(tvls):
    """Calculate risk score based on TVL using relative values"""
    # Convert to numpy array for vectorized operations
    tvl_values = np.array(tvls)
    # Normalize to 0-1 range where 1 is highest risk (lowest TVL)
    max_tvl = np.max(tvl_values)
    return 1 - (tvl_values / max_tvl)


def calculate_volatility_from_risk(risk_score):
    """Convert risk score to volatility using a linear scale"""
    # Map risk scores to volatility range of 4% to 20%
    return 0.04 + (risk_score * 0.16)


def kelly_allocation(expected_returns, protocol_ages, tvls, pool_names=None, rf=0.0):
    """
    Calculate Kelly-optimal allocation weights for multiple stablecoin pools using protocol age and TVL for risk assessment.

    Parameters:
    - expected_returns: list or np.array of expected APY for each pool
    - protocol_ages: list of protocol ages in months
    - tvls: list of TVL values in USD
    - pool_names: list of pool names — optional
    - rf: risk-free rate, default is 0

    Returns:
    - Dictionary of pool_name -> weight (as percentage)
    """
    expected_returns = np.array(expected_returns)
    if pool_names is None:
        pool_names = [f"Pool_{i+1}" for i in range(len(expected_returns))]

    # Calculate risk scores and convert to volatility
    age_risks = calculate_age_risk(protocol_ages)
    tvl_risks = calculate_tvl_risk(tvls)

    # Combine risks (40% age, 60% TVL weight)
    combined_risks = (age_risks * 0.4) + (tvl_risks * 0.6)
    volatilities = calculate_volatility_from_risk(combined_risks)

    # Covariance matrix assuming independence (diagonal only)
    cov_matrix = np.diag(volatilities**2)
    excess_return = expected_returns - rf

    # Kelly formula
    inv_cov = np.linalg.inv(cov_matrix)
    raw_weights = inv_cov.dot(excess_return)
    norm_weights = raw_weights / raw_weights.sum()  # Normalize to sum to 1

    # Format result
    return {
        name: round(weight * 100, 2) for name, weight in zip(pool_names, norm_weights)
    }


# Example usage
expected_returns = [0.5, 0.11, 0.138]  # Expected APYs
protocol_ages = [36, 34, 41]  # Protocol ages in months
tvls = [339, 1010, 27]  # TVL in M USD
pool_names = ["aster", "aerodrome", "gains"]

weights = kelly_allocation(expected_returns, protocol_ages, tvls, pool_names)
print("\nKelly Optimal Allocation Weights:")
print("-" * 30)
for pool, weight in weights.items():
    print(f"{pool}: {weight:.2f}%")
print("-" * 30)
