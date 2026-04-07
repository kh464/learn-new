from pathlib import Path


def test_dev_scripts_enable_utf8_console_and_python() -> None:
    dev_script = Path("scripts/dev.ps1").read_text(encoding="utf-8")
    test_script = Path("scripts/test.ps1").read_text(encoding="utf-8")

    assert "chcp 65001" in dev_script
    assert "$env:PYTHONUTF8='1'" in dev_script
    assert "uvicorn app.main:app --reload" in dev_script

    assert "chcp 65001" in test_script
    assert "$env:PYTHONUTF8='1'" in test_script
    assert "pytest tests -q" in test_script


def test_backup_and_restore_scripts_include_operational_safety_guards() -> None:
    backup_script = Path("scripts/backup.ps1").read_text(encoding="utf-8")
    restore_script = Path("scripts/restore.ps1").read_text(encoding="utf-8")

    assert "[switch]$IncludeConfig" in backup_script
    assert "backup-manifest.json" in backup_script
    assert "Copy-Item -LiteralPath" in backup_script

    assert "[switch]$Force" in restore_script
    assert "backup-manifest.json" in restore_script
    assert "throw \"Backup archive does not contain backup-manifest.json" in restore_script
    assert "throw \"Refusing to remove existing .learn without -Force." in restore_script


def test_observability_compose_templates_exist() -> None:
    compose_file = Path("docker-compose.observability.yml").read_text(encoding="utf-8")
    prometheus_file = Path("ops/prometheus/prometheus.yml").read_text(encoding="utf-8")
    datasource_file = Path("ops/grafana/provisioning/datasources/prometheus.yml").read_text(encoding="utf-8")
    alert_rules_file = Path("ops/prometheus/alerts.yml").read_text(encoding="utf-8")

    assert "prometheus:" in compose_file
    assert "grafana:" in compose_file
    assert "/metrics" in prometheus_file
    assert "Prometheus" in datasource_file
    assert "LearnNewAppDown" in alert_rules_file


def test_edge_and_cluster_templates_exist() -> None:
    edge_compose = Path("docker-compose.edge.yml").read_text(encoding="utf-8")
    caddyfile = Path("ops/caddy/Caddyfile").read_text(encoding="utf-8")
    deployment = Path("ops/k8s/deployment.yaml").read_text(encoding="utf-8")
    service = Path("ops/k8s/service.yaml").read_text(encoding="utf-8")
    ingress = Path("ops/k8s/ingress.yaml").read_text(encoding="utf-8")

    assert "caddy:" in edge_compose
    assert "reverse_proxy app:8000" in caddyfile
    assert "kind: Deployment" in deployment
    assert "kind: Service" in service
    assert "kind: Ingress" in ingress


def test_helm_chart_templates_exist() -> None:
    chart = Path("ops/helm/learn-new/Chart.yaml").read_text(encoding="utf-8")
    values = Path("ops/helm/learn-new/values.yaml").read_text(encoding="utf-8")
    deployment = Path("ops/helm/learn-new/templates/deployment.yaml").read_text(encoding="utf-8")
    service = Path("ops/helm/learn-new/templates/service.yaml").read_text(encoding="utf-8")
    ingress = Path("ops/helm/learn-new/templates/ingress.yaml").read_text(encoding="utf-8")
    hpa = Path("ops/helm/learn-new/templates/hpa.yaml").read_text(encoding="utf-8")
    pdb = Path("ops/helm/learn-new/templates/pdb.yaml").read_text(encoding="utf-8")
    configmap = Path("ops/helm/learn-new/templates/configmap.yaml").read_text(encoding="utf-8")
    secret = Path("ops/helm/learn-new/templates/secret.yaml").read_text(encoding="utf-8")
    serviceaccount = Path("ops/helm/learn-new/templates/serviceaccount.yaml").read_text(encoding="utf-8")
    role = Path("ops/helm/learn-new/templates/role.yaml").read_text(encoding="utf-8")
    rolebinding = Path("ops/helm/learn-new/templates/rolebinding.yaml").read_text(encoding="utf-8")
    networkpolicy = Path("ops/helm/learn-new/templates/networkpolicy.yaml").read_text(encoding="utf-8")

    assert "apiVersion: v2" in chart
    assert "image:" in values
    assert ".Values.image.repository" in deployment
    assert "kind: Service" in service
    assert "kind: Ingress" in ingress
    assert "kind: HorizontalPodAutoscaler" in hpa
    assert "kind: PodDisruptionBudget" in pdb
    assert "kind: ConfigMap" in configmap
    assert "kind: Secret" in secret
    assert "kind: ServiceAccount" in serviceaccount
    assert "kind: Role" in role
    assert "kind: RoleBinding" in rolebinding
    assert "kind: NetworkPolicy" in networkpolicy
