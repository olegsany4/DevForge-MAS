# mas/cli.py — CLI оболочка поверх WorkflowRunner
from __future__ import annotations

import click

from mas.core.workflow import WorkflowRunner


@click.group()
def main():
    """DevForge-MAS CLI."""
    # Ничего не делаем в корневой группе.


@main.command()
@click.option("--workflow", required=True, type=click.Path(exists=True))
@click.option("--request", required=True, type=click.Path(exists=True))
@click.option("--agents", default="configs/agents.yaml", type=click.Path(exists=True))
@click.option("--workspace", default="workspace", type=click.Path())
@click.option(
    "--skip-optional",
    multiple=True,
    help="IDs шагов для пропуска (можно указывать несколько).",
)
def run(workflow, request, agents, workspace, skip_optional):
    runner = WorkflowRunner(workspace, agents, workflow)
    result = runner.run(request, skip_optional=skip_optional)
    click.echo(result)


if __name__ == "__main__":
    main()
