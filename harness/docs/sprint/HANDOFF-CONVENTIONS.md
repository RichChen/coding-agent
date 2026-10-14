# 交接文件约定

`docs/sprint/memory-source-runs.json` 在 Windows 上保存为 CRLF。sha256 不直接对磁盘字节计算。

两边都用 `scripts/handoff_sha.py` 里的 `handoff_sha256`：读取文件，把换行归一化成 LF，再对 UTF-8 字节做 SHA-256。

```python
def handoff_sha256(path: Path) -> str:
    text = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(text).hexdigest()
```
