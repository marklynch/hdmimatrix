Deploy instructions

## Dependencies
```
pip3 install build twine
```

## Build it
```
python -m build
```


Test upload
```
python3 -m twine upload --repository testpypi dist/*
```


Real upload
```
python3 -m twine upload dist/*
```