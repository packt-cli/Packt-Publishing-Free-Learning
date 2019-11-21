## Release process

First install development dependencies. Make sure you're on `master` branch with all changes that are going to be released.

```
pip install -e '.[dev]'
```

Then run `bumpversion part` to bump version of the script. `part` may be either `patch`, `minor` or `major`, decide
which one to use according to [semantic versioning](https://semver.org/). `bumpversion` will bump script's version
in files inside repository, commit the changes and tag the commit with `vX.Y.Z` tag, where `X.Y.Z` is the current
version of the script. Now push the commit and the tag.

```
git push origin && git push origin vX.Y.Z
```

The new version has already been tagged in `git` repository, now it's time to release a new version on [PyPI](https://pypi.org/project/packt/). Run `python setup.py sdist` to build the package for the new release, check if build was successful by running `twine check dist/*`. If everything is alright run

```
twine upload dist/*
```

to release a new version to PyPI.
