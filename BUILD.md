# Deploy instructions

## Dependencies
```
pip3 install build twine
```

## Build it
```
python3 -m build
```

## Test upload. 
To: https://testpypi.org/project/hdmimatrix/
```
python3 -m twine upload --repository testpypi dist/*
```

## Real upload.
To:  https://pypi.org/project/hdmimatrix/
```
python3 -m twine upload dist/*
```