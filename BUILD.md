# Release instructions

Releases are published to PyPI automatically by GitHub Actions
(`.github/workflows/release.yml`) when a `v*` tag is pushed.

## Releasing

1. Bump `version` in `pyproject.toml` and move the `[Unreleased]` notes in
   `CHANGELOG.md` under the new version heading.
2. Commit and push to `main`.
3. Tag and push — the tag must match the `pyproject.toml` version:
   ```
   git tag v0.7.0
   git push origin v0.7.0
   ```

The workflow then:

1. Runs the full test matrix (Python 3.10–3.13) and the lint job. Nothing is
   published if either fails.
2. Verifies the tag matches the version in `pyproject.toml`.
3. Builds the sdist + wheel and runs `twine check`.
4. Publishes to PyPI via trusted publishing (OIDC — no API token stored in the repo).

## One-time PyPI setup

Trusted publishing must be configured once on PyPI before the first automated
release, at https://pypi.org/manage/project/hdmimatrix/settings/publishing/:

- Owner: `marklynch`
- Repository name: `hdmimatrix`
- Workflow name: `release.yml`
- Environment name: `pypi`

Then create a `pypi` environment in the repository settings
(Settings → Environments). Optionally add a required reviewer there if you want
a manual approval step between "tests passed" and "published".

## Manual release (fallback)

```
pip3 install build twine
python3 -m build
python3 -m twine upload --repository testpypi dist/*   # https://test.pypi.org/project/hdmimatrix/
python3 -m twine upload dist/*                          # https://pypi.org/project/hdmimatrix/
```
