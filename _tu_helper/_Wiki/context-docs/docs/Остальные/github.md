## pull-request
categories: Dev - GitHub - Workflow
aliases: pr, merge request
Pull Request — предложение изменений с обсуждением.
```text
Open PR -> request reviews -> fix -> merge
```

---

## actions
categories: Dev - GitHub - CI
aliases: workflow, gha
GitHub Actions — CI/CD на основе workflow-файлов.
```yaml
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
```
