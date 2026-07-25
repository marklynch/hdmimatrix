# Release instructions

Releases are published to PyPI automatically by GitHub Actions
(`.github/workflows/release.yml`) when a `v*` tag is pushed.

The version is not stored in `pyproject.toml`. `setuptools-scm` derives it from the
git tag, so tagging `v0.7.0` publishes 0.7.0 and there is no version field to keep
in sync.

## Releasing

1. Move the `[Unreleased]` notes in `CHANGELOG.md` under the new version heading.
2. Commit and push to `main`.
3. Tag and push:
   ```
   git tag v0.7.0
   git push origin v0.7.0
   ```

The workflow then:

1. Runs the full test matrix (Python 3.10–3.13), lint, and type check. Nothing is
   published if any of them fail.
2. Builds the sdist + wheel from the tag and runs `twine check`.
3. Verifies the built distributions carry the tag's version, which catches a
   checkout that did not have the tag available.
4. Publishes to PyPI via trusted publishing (OIDC — no API token stored in the repo).

Builds from an untagged commit get a development version derived from the last tag
(for example `0.6.1.dev5+gf791817`), so a local `python3 -m build` will not produce
a release version by accident.

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
