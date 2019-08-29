Harvest the interface changes from the HTML version of the ESMF reference manual from two different tags and then `diff` them to make a report.

The main run target is `./src/esmf_api_changes/esmf_api_changes.py`.

## Usage

1. Customize the User Environment Variables in `esmf_api_changes.py`. The script should work with the defaults.
2. Then, run the script using Python 3 (not compatible with Python 2.7):
```shell script
$ python3 <path/to>/esmf_api_changes.py 2>&1 | tee esmf_api_changes.out
```