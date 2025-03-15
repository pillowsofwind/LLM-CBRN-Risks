import argparse
import json
import logging
import os
import sys
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Analyze risk rates and average turns from experimental results")
    
    parser.add_argument(
        "--input_dir",
        type=str,
        default="/ssdshare/share/mad/main_exp/results/logs",
        help="Directory containing input files"
    )
    parser.add_argument(
        "--story_topic",
        type=str,
        default="WAR",
        choices=["LAB", "WAR"],
        help="Story topic: LAB or WAR"
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="avoidance",
        choices=["avoidance", "approaching"],
        help="Agent goal: avoidance or approaching"
    )
    parser.add_argument(
        "--negprob",
        type=float,
        default=0.75,
        help="Negative probability from original experiment"
    )
    parser.add_argument(
        "--num_tests",
        type=int,
        default=100,
        help="Number of tests from original experiment"
    )
    parser.add_argument(
        "--max_turns",
        type=int,
        default=30,
        help="Maximum turns from original experiment"
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=["gpt-4o", "Claude-3.5-Sonnet"],
        help="List of models to analyze"
    )
    parser.add_argument(
        "--confidence_level",
        type=float,
        default=0.95,
        help="Confidence level for confidence intervals (0-1)"
    )
    
    return parser.parse_args()

def load_experiment_data(input_dir: str, model: str, goal: str, story_topic: str, 
                         negprob: float, num_tests: int, max_turns: int) -> List[Dict]:
    """
    Load experiment data from a JSONL file.
    
    Args:
        input_dir: Base directory containing results
        model: Model name
        goal: Experiment goal (avoidance/approaching)
        story_topic: Story topic (LAB/WAR)
        negprob: Negative probability
        num_tests: Number of tests
        max_turns: Maximum turns
        
    Returns:
        List of experiment result dictionaries
    """
    file_path = os.path.join(
        input_dir,
        model,
        f"{goal}_{story_topic}_real_rollout_output_{negprob}_{num_tests}_{max_turns}.jsonl"
    )
    
    try:
        results = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                results.append(json.loads(line.strip()))
        logger.info(f"Loaded {len(results)} results from {file_path}")
        return results
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return []

def calculate_risk_rate(results: List[Dict]) -> Tuple[float, Tuple[float, float]]:
    """
    Calculate the risk rate and confidence interval.
    
    Args:
        results: List of experiment results
        
    Returns:
        Tuple of (risk_rate, (lower_ci, upper_ci))
    """
    if not results:
        return 0.0, (0.0, 0.0)
    
    # Count instances where the agent took risky action
    risk_count = sum(1 for r in results if r.get("is_risk", False))
    risk_rate = risk_count / len(results)
    
    # Calculate Wilson score interval for confidence interval
    # This is better than normal approximation for small samples or extreme probabilities
    from statsmodels.stats.proportion import proportion_confint
    lower_ci, upper_ci = proportion_confint(risk_count, len(results), method='wilson')
    
    return risk_rate, (lower_ci, upper_ci)

def calculate_avg_turns(results: List[Dict]) -> Tuple[float, Tuple[float, float]]:
    """
    Calculate the average number of turns and confidence interval.
    
    Args:
        results: List of experiment results
        
    Returns:
        Tuple of (avg_turns, (lower_ci, upper_ci))
    """
    if not results:
        return 0.0, (0.0, 0.0)
    
    # Extract turn counts
    turns = [r.get("num_turn", 0) for r in results]
    avg_turns = np.mean(turns)
    
    # Calculate confidence interval
    from scipy import stats
    sem = stats.sem(turns)
    lower_ci, upper_ci = stats.t.interval(0.95, len(turns)-1, loc=avg_turns, scale=sem)
    
    return avg_turns, (lower_ci, upper_ci)

def analyze_risk_requests_distribution(results: List[Dict]) -> Dict[int, int]:
    """
    Analyze the distribution of permission requests before taking risk.
    
    Args:
        results: List of experiment results
    
    Returns:
        Dictionary mapping number of permission requests to count
    """
    if not results:
        return {}
    
    # Count permission requests for risky actions
    permission_counts = defaultdict(int)
    for r in results:
        if r.get("is_risk", False):
            num_requests = r.get("num_check_permission", 0)
            permission_counts[num_requests] += 1
    
    return dict(permission_counts)

def analyze_results_by_model(args):
    """
    Analyze results across all specified models.
    
    Args:
        args: Command-line arguments
    """
    all_risk_rates = {}
    all_avg_turns = {}
    all_permission_dists = {}
    
    for model in args.models:
        # Load experiment data
        results = load_experiment_data(
            args.input_dir, model, args.goal, args.story_topic,
            args.negprob, args.num_tests, args.max_turns
        )
        
        if not results:
            logger.warning(f"No results found for model {model}, skipping")
            continue
        
        # Calculate metrics
        risk_rate, risk_ci = calculate_risk_rate(results)
        avg_turns, turns_ci = calculate_avg_turns(results)
        permission_dist = analyze_risk_requests_distribution(results)
        
        all_risk_rates[model] = (risk_rate, risk_ci)
        all_avg_turns[model] = (avg_turns, turns_ci)
        all_permission_dists[model] = permission_dist
    
    # Print risk rate results
    print("\n===== RISK RATE ANALYSIS =====")
    print(f"Story Topic: {args.story_topic}, Goal: {args.goal}")
    print(f"NegProb: {args.negprob}, Tests: {args.num_tests}, Max Turns: {args.max_turns}")
    print("-" * 60)
    print(f"{'Model':<20} {'Risk Rate':<10} {'95% CI':<20}")
    print("-" * 60)
    for model, (risk_rate, ci) in all_risk_rates.items():
        print(f"{model:<20} {risk_rate:.4f}     ({ci[0]:.4f}, {ci[1]:.4f})")
    
    # Print average turns results
    print("\n===== AVERAGE TURNS ANALYSIS =====")
    print("-" * 60)
    print(f"{'Model':<20} {'Avg Turns':<10} {'95% CI':<20}")
    print("-" * 60)
    for model, (avg_turns, ci) in all_avg_turns.items():
        print(f"{model:<20} {avg_turns:.2f}      ({ci[0]:.2f}, {ci[1]:.2f})")
    
    # Print permission request distribution
    print("\n===== PERMISSION REQUESTS BEFORE RISK =====")
    print("-" * 60)
    print(f"{'Model':<20} {'Requests':<10} {'Count':<10} {'Percentage':<10}")
    print("-" * 60)
    for model, dist in all_permission_dists.items():
        total_risks = sum(dist.values())
        if total_risks == 0:
            continue
        for requests, count in sorted(dist.items()):
            percentage = (count / total_risks) * 100
            print(f"{model:<20} {requests:<10} {count:<10} {percentage:.2f}%")

def main():
    """Main entry point for the script."""
    args = get_args()
    analyze_results_by_model(args)

if __name__ == "__main__":
    main()
