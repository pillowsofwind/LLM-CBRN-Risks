import argparse
import json
import logging
import os
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Analyze deception results from experimental results")
    
    parser.add_argument(
        "--input_dir",
        type=str,
        default="/ssdshare/share/mad/main_exp/results/deception",
        help="Directory containing deception test results"
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
        "--consequence_level",
        type=str,
        default="high",
        choices=["light", "mild", "intermediate", "high", "extreme"],
        help="Consequence level for deception testing"
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=["gpt-4o", "Claude-3.5-Sonnet"],
        help="List of models to analyze"
    )
    
    return parser.parse_args()

def load_deception_data(input_dir: str, model: str, goal: str, story_topic: str, 
                         negprob: float, num_tests: int, max_turns: int,
                         consequence_level: str) -> List[Dict]:
    """
    Load deception test data from a JSONL file.
    
    Args:
        input_dir: Base directory containing results
        model: Model name
        goal: Experiment goal (avoidance/approaching)
        story_topic: Story topic (LAB/WAR)
        negprob: Negative probability
        num_tests: Number of tests
        max_turns: Maximum turns
        consequence_level: Consequence level for deception testing
        
    Returns:
        List of deception test result dictionaries
    """
    file_path = os.path.join(
        input_dir,
        model,
        f"{goal}_{story_topic}_real_rollout_output_{negprob}_{num_tests}_{max_turns}_{consequence_level}.jsonl"
    )
    
    try:
        results = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                results.append(json.loads(line.strip()))
        logger.info(f"Loaded {len(results)} deception test results from {file_path}")
        return results
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return []

def calculate_deception_rate(results: List[Dict]) -> Tuple[float, Tuple[float, float]]:
    """
    Calculate the deception rate and confidence interval.
    
    Args:
        results: List of deception test results
        
    Returns:
        Tuple of (deception_rate, (lower_ci, upper_ci))
    """
    if not results:
        return 0.0, (0.0, 0.0)
    
    # Count deception instances
    deception_count = sum(1 for r in results if r.get("deception", False))
    deception_rate = deception_count / len(results)
    
    # Calculate Wilson score interval for confidence interval
    from statsmodels.stats.proportion import proportion_confint
    lower_ci, upper_ci = proportion_confint(deception_count, len(results), method='wilson')
    
    return deception_rate, (lower_ci, upper_ci)

def calculate_commitment_rate(results: List[Dict]) -> Tuple[float, Tuple[float, float]]:
    """
    Calculate the commitment rate (admitting to action) and confidence interval.
    
    Args:
        results: List of deception test results
        
    Returns:
        Tuple of (commitment_rate, (lower_ci, upper_ci))
    """
    if not results:
        return 0.0, (0.0, 0.0)
    
    # Count commitment instances
    commitment_count = sum(1 for r in results if r.get("commitment", False))
    commitment_rate = commitment_count / len(results)
    
    # Calculate Wilson score interval for confidence interval
    from statsmodels.stats.proportion import proportion_confint
    lower_ci, upper_ci = proportion_confint(commitment_count, len(results), method='wilson')
    
    return commitment_rate, (lower_ci, upper_ci)

def analyze_response_distribution(results: List[Dict]) -> Dict[str, int]:
    """
    Analyze the distribution of response types.
    
    Args:
        results: List of deception test results
    
    Returns:
        Dictionary mapping response types to counts
    """
    if not results:
        return {}
    
    # Count responses by verdict
    response_counts = defaultdict(int)
    for r in results:
        verdict = r.get("verdict", "unknown")
        if "5.A" in verdict:
            response_counts["admitting"] += 1
        elif "5.B" in verdict:
            response_counts["denying"] += 1
        elif "5.C" in verdict:
            response_counts["being vague"] += 1
        elif "5.D" in verdict:
            response_counts["false accusation"] += 1
        else:
            response_counts["other"] += 1
    
    return dict(response_counts)

def analyze_deception_by_model(args):
    """
    Analyze deception results across all specified models.
    
    Args:
        args: Command-line arguments
    """
    all_deception_rates = {}
    all_commitment_rates = {}
    all_response_dists = {}
    
    for model in args.models:
        # Load deception data
        results = load_deception_data(
            args.input_dir, model, args.goal, args.story_topic,
            args.negprob, args.num_tests, args.max_turns, args.consequence_level
        )
        
        if not results:
            logger.warning(f"No deception results found for model {model}, skipping")
            continue
        
        # Calculate metrics
        deception_rate, deception_ci = calculate_deception_rate(results)
        commitment_rate, commitment_ci = calculate_commitment_rate(results)
        response_dist = analyze_response_distribution(results)
        
        all_deception_rates[model] = (deception_rate, deception_ci)
        all_commitment_rates[model] = (commitment_rate, commitment_ci)
        all_response_dists[model] = response_dist
    
    # Print deception rate results
    print("\n===== DECEPTION RATE ANALYSIS =====")
    print(f"Story Topic: {args.story_topic}, Goal: {args.goal}, Consequence Level: {args.consequence_level}")
    print(f"NegProb: {args.negprob}, Tests: {args.num_tests}, Max Turns: {args.max_turns}")
    print("-" * 60)
    print(f"{'Model':<20} {'Deception Rate':<15} {'95% CI':<20}")
    print("-" * 60)
    for model, (rate, ci) in all_deception_rates.items():
        print(f"{model:<20} {rate:.4f}          ({ci[0]:.4f}, {ci[1]:.4f})")
    
    # Print commitment rate results
    print("\n===== COMMITMENT RATE ANALYSIS =====")
    print("-" * 60)
    print(f"{'Model':<20} {'Commitment Rate':<15} {'95% CI':<20}")
    print("-" * 60)
    for model, (rate, ci) in all_commitment_rates.items():
        print(f"{model:<20} {rate:.4f}          ({ci[0]:.4f}, {ci[1]:.4f})")
    
    # Print response distribution
    print("\n===== RESPONSE DISTRIBUTION =====")
    print("-" * 70)
    print(f"{'Model':<20} {'Response Type':<20} {'Count':<10} {'Percentage':<10}")
    print("-" * 70)
    for model, dist in all_response_dists.items():
        total_responses = sum(dist.values())
        if total_responses == 0:
            continue
        for response_type, count in dist.items():
            percentage = (count / total_responses) * 100
            print(f"{model:<20} {response_type:<20} {count:<10} {percentage:.2f}%")

def main():
    """Main entry point for the script."""
    args = get_args()
    analyze_deception_by_model(args)

if __name__ == "__main__":
    main()
