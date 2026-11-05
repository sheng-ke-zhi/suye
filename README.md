# 夙夜 · SUYE

`suye doctor` 是一个只读的开发工具链诊断命令，适用于排查 SUYE 开发环境中
“工具已安装，但终端找不到”的问题。Python 包和 Rust 二进制提供相同的诊断功能；
两者是独立发行方式，不需要同时安装。首版不是投研引擎，也不会连接行情或交易系统。

## 使用

```text
suye doctor
suye --version
suye --help
```

按顺序检查 `git`、`python3`、`cargo`、`rustc` 在当前 `PATH` 上是否存在可执行文件，
输出 `[OK]` 或 `[MISSING]`。这些是完整开发工具链检查项，不是运行此诊断命令的全部依赖。
缺失时提示将对应工具加入 `PATH`，但不会替用户修改环境。

- 退出码：`0` 表示四项均可发现；`1` 表示有缺失项；`2` 表示命令参数错误。
- `PATH` 未设置或为空时，四项均报缺失，不回退搜索系统默认目录。
- 不执行被检查程序，不检查其版本或运行健康状态，也不证明安装完整或版本兼容。
- 不联网、不安装工具、不读凭据、不修改配置、不打印工具路径或环境变量值。
- Unix 检查普通文件及执行权限位；Windows 检查对应 `.exe` 文件。
  Python 使用标准库 `shutil.which`，也可识别 Windows `PATHEXT` 中的其他后缀；
  Rust 首版只识别 `.exe`。文件系统 ACL、`noexec` 挂载等可能导致发现的工具仍不可运行。
- 若四项均为 `OK` 但工具不能启动，应手动检查对应工具的版本、权限和安装状态。
- 两种发行方式都提供名为 `suye` 的命令，建议选用一种，避免命令覆盖或 PATH 优先级歧义。

## 本地验证（无需安装新软件）

Python 需要已有 Python 3.9+；Rust 需要已有 Cargo/Rust 工具链。

```sh
PYTHONPATH=python python3 -m suye doctor
PYTHONPATH=python python3 -m unittest discover -s tests -p 'test_*.py'
cargo run --offline -- doctor
cargo test --offline
cargo fmt --check
cargo clippy --offline --all-targets -- -D warnings
```

已有 setuptools 58+ 和 wheel 时，可在不下载依赖、不安装包的情况下构建 Python wheel：

```sh
python3 -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist .
python3 -c 'from setuptools.build_meta import build_sdist; build_sdist("dist")'
cargo package --offline
```

## 发布前置条件

仓库保持私有。**上传 PyPI/crates.io 后，包内源码、README 和元数据会公开，
即使 GitHub 仓库仍为私有。** 当前未获得许可证和公开包内容确认，不附加任何开源许可证，
不配置自动发布流程；Cargo 设置 `publish = false` 防止误发布。
本地构建成功不代表平台已接受、名称可注册或包已发布。

正式发布前必须：

1. 由用户确认许可证及允许公开的源码、文档和元数据，审核两个发行归档的文件清单。
2. 复核版本号和名称可用性。PyPI 的 PEP 541 与 crates.io 使用政策限制纯占名包；
   本项目应作为实际工具维护，不以无功能包占名。
3. 配置用户批准的安全发布授权（例如受信发布或安全凭据配置），不得把令牌写入仓库、
   日志或评论。私有 GitHub 仓库本身不赋予任何包索引发布权限。
4. 经审核解除 Cargo 的发布禁用，再分别执行平台所需的构建、检查及发布步骤。

政策入口：<https://peps.python.org/pep-0541/#invalid-projects>、<https://crates.io/policies>。
发布授权说明：<https://docs.pypi.org/trusted-publishers/>、
<https://doc.rust-lang.org/cargo/reference/publishing.html>。
