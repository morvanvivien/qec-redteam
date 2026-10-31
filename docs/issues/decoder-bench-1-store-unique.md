`generator.py` declares the flag with `type=bool`:

```python
parser.add_argument('--store_unique', type=bool, default=True, help='Store only unique syndromes (default: True)')
```

argparse calls `bool()` on the string, and `bool("False")` is `True`, so every non-empty value keeps deduplication on:

```
['--store_unique', 'False'] -> True
['--store_unique', '0']     -> True
['--store_unique', 'no']    -> True
['--store_unique', '']      -> False
```

A possible fix that keeps the current default:

```python
parser.add_argument('--store_unique', action=argparse.BooleanOptionalAction, default=True)
```

This gives `--store_unique` and `--no-store_unique`. Happy to open a PR if that helps.

Checked on master at 9733a55.
