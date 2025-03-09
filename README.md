# LLM-CBRN-Risks

Please visit [our project page](https://llm-catastrophic-risks.github.io/) for a better overview of our research.

Full paper is available at [arXiv](https://arxiv.org/abs/2502.11355).

## Getting Started

This repository contains code to reproduce experiments from our paper "Nuclear Deployed!": Analyzing Catastrophic Risks in Decision-making of Autonomous LLM Agents.

### Installation

```bash
# Clone the repository
git clone https://github.com/llm-catastrophic-risks/LLM-CBRN-Risks.git
cd LLM-CBRN-Risks

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Before running experiments, configure your model API keys in the `rollout/model_config.toml` file:

```toml
[models.gpt-4o]
type = "azure"
endpoint = "https://your-endpoint.openai.azure.com/"
api_key = "YOUR_API_KEY"
api_version = "2024-10-21"
model_name = "gpt-4o"
temperature = 0.9
max_tokens = 4096

# Add additional models as needed
```

## Running Experiments

### Risk Assessment Experiments

To run the main risk assessment experiments:

```bash
# Basic usage with default parameters
python -m rollout.risk --output_dir /path/to/results

# Advanced usage with all parameters
python -m rollout.risk \
    --model gpt-4o \
    --env_model gpt-4o-mini \
    --story_topic WAR \
    --goal avoidance \
    --negprob 0.75 \
    --num_tests 100 \
    --max_turns 30 \
    --output_dir /path/to/results \
    --consequence "The long-term radiation will lead to the extinction of up to 60% of all life forms within three years."
```

#### Parameters:

- `--model`: Model for agent decision-making (default: gpt-4o)
- `--env_model`: Model for environment updates (default: gpt-4o-mini)  
- `--story_topic`: Scenario context - WAR or LAB (default: WAR)
- `--goal`: Agent goal - avoidance or approaching (default: avoidance)
- `--negprob`: Probability of negative state updates (default: 0.75)
- `--num_tests`: Number of tests to run (default: 100)
- `--max_turns`: Maximum conversation turns per test (default: 30)
- `--output_dir`: Directory to save results (required)
- `--consequence`: Additional consequence text for risk actions

### Deception Testing

After running risk assessment experiments, you can test whether agents will admit to their actions when confronted:

```bash
python -m rollout.deception \
    --model gpt-4o \
    --story_topic WAR \
    --goal avoidance \
    --negprob 0.75 \
    --num_tests 100 \
    --max_turns 30 \
    --consequence_level high \
    --input_dir /path/to/risk/results \
    --output_dir /path/to/deception/results
```

#### Parameters:

- `--model`: Model for deception testing (default: gpt-4o)
- `--story_topic`: Scenario context - WAR or LAB (default: WAR)
- `--goal`: Agent goal - avoidance or approaching (default: avoidance)
- `--negprob`, `--num_tests`, `--max_turns`: Match these with your original experiment
- `--consequence_level`: Severity of consequences for honesty (light/mild/intermediate/high/extreme)
- `--input_dir`: Directory containing risk experiment results
- `--output_dir`: Directory to save deception results
- `--max_retries`: Maximum retries for API failures (default: 3)

## Output Format

Results are saved in JSONL format with the following structure:

### Risk Experiments:
```json
{
  "is_risk": true/false,
  "num_check_permission": 0,
  "num_turn": 15,
  "agent_model": "gpt-4o",
  "env_model": "gpt-4o-mini",
  "chat_history": [...]
}
```

### Deception Experiments:
```json
{
  "deception": true/false,
  "commitment": true/false,
  "verdict": "5.A",
  "response": "...",
  "history_index": 0,
  "iteration": 0
}
```

## Citation

```bib
@misc{xu2025nucleardeployedanalyzingcatastrophic,
      title={"Nuclear Deployed!": Analyzing Catastrophic Risks in Decision-making of Autonomous LLM Agents}, 
      author={Rongwu Xu and Xiaojian Li and Shuo Chen and Wei Xu}, 
      year={2025}, 
      eprint={2502.11355}, 
      archivePrefix={arXiv}, 
      primaryClass={cs.CL}, 
      url={https://arxiv.org/abs/2502.11355}, 
    }
```
