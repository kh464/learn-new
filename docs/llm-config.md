# LLM Configuration

The project uses `config/llm.yaml` as the model configuration file.

## Current default

- Default provider: `siliconflow`
- API key source: environment variable `SILICONFLOW_API_KEY`
- Recommended local template: `.env.example`

## File structure

`config/llm.yaml` is split into three parts:

1. `llm.default_provider` and `llm.default_profile`
2. `llm.providers.<provider>` for provider connection details
3. `llm.routing.profiles` for task-to-model mapping

## How to set the API key

Temporary for the current PowerShell session:

```powershell
$env:SILICONFLOW_API_KEY="your_real_api_key"
```

Permanent for the current Windows user:

```powershell
[Environment]::SetEnvironmentVariable("SILICONFLOW_API_KEY", "your_real_api_key", "User")
```

After setting it, restart the terminal or reload the shell before starting the app.

## How to switch models

Edit `config/llm.yaml` and replace the values under:

- `llm.providers.siliconflow.models`
- `llm.routing.profiles`

Keep the provider name and model mapping aligned.

## How to add another provider later

1. Add a new block under `llm.providers`
2. Use an environment variable for `api_key`
3. Add matching entries under `llm.routing.profiles`

Example environment variables:

```powershell
$env:OPENAI_API_KEY="your_openai_key"
$env:ANTHROPIC_API_KEY="your_anthropic_key"
$env:DEEPSEEK_API_KEY="your_deepseek_key"
```
