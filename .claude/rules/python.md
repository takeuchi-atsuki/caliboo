---
paths:
  - "**/*.py"
---

# Python

- Pythonで引数を扱うとき、未使用の引数を `_*` とするのは原則禁止。  
  後から見て何の引数か意味が分からないため、ちゃんと命名すること（前方 `_` は問題ない）  

  - 例：元ソース

    ```python
    def __exit__(self, exc_type, exc, tb):
    ```

  - 例：悪いリファクタリング

    ```python
    def __exit__(self, _*):
    ```

  - 例：良いリファクタリング

    ```python
    def __exit__(self, _exc_type, _exc, _tb):
    ```
