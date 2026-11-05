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

## GitHub Actions 与发布

仓库已按用户授权公开。**上传 PyPI/crates.io 还会公开发行归档中的源码、README 和元数据。**
公开仓库不等于已经选择开源许可证；许可证仍待用户确认，当前保留 `publish = false`。
本地构建或 CI 成功不代表包已发布，也不保证名称可注册。

流程文件是 `.github/workflows/release.yml`，Actions 页面显示为 **Build and publish**：

- PR 和 main 分支更新只运行版本检查、Python/Rust 测试、格式/Clippy、构建与归档验证。
- 正式上传仅限在 main 上手动 **Run workflow**，并明确勾选 `publish`。
  创建 tag 或 GitHub Release 本身不会上传包。
- 手动运行必须提供已有的稳定版本 tag（例如 `v0.1.0`），且该提交必须属于 main 历史。
  tag、`setup.cfg`、`suye.__version__`、`Cargo.toml` 必须一致；Cargo 使用 `--locked`。
- 上传前还要求 LICENSE 非空、两个清单的 SPDX 许可证表达式一致、Cargo 明确允许 crates.io。
  构建/校验任务没有 OIDC 权限，只有两个发布任务有 `id-token: write`，不需要仓库写权限。
- PyPI 使用同次运行构建的 artifact；crates.io 固定 checkout 已验证的提交 SHA。
  所有外部 Action 固定到提交 SHA，不使用可移动标签。
- `publish=false`（默认）只做构建演练，不验证平台登录或执行环境审核；
  `publish=true` 才额外校验许可证、执行 Cargo 发布预检，再进入发布环境审核和上传。

### 第一步：许可证与版本（发布前必做）

由项目负责人确定许可证，通过审核后的提交加入：

1. 根目录 `LICENSE`：用户确认的完整许可证文本。
2. `setup.cfg` 的 `[metadata]`：加入 `license = 用户确认的 SPDX 表达式`。
3. `Cargo.toml` 的 `[package]`：加入完全相同的 `license` 字段，
   并将 `publish = false` 改为 `publish = ["crates-io"]`。

本项目不代选许可证。发布脚本和测试使用 Python 3.11+（CI 为 3.12），可独立检查：

```sh
python3.12 scripts/check_release.py
python3.12 -m unittest discover -s scripts -p 'test_*.py'
python3.12 scripts/check_release.py --tag v0.1.0 --publish
```

最后一条在尚未确认许可证时应失败，这不是普通构建失败。
后续版本需同步修改 `setup.cfg`、`python/suye/__init__.py`、`Cargo.toml`，
再运行 `cargo generate-lockfile --offline`，将更新后的 `Cargo.lock` 一并提交审核。

### 第二步：GitHub 需要配置什么

打开 `sheng-ke-zhi/suye` → **Settings → Environments → New environment**，建立以下环境：

| 准确名称 | 是否必需 | 用途及设置 |
| --- | --- | --- |
| `pypi` | 发布 PyPI 必需 | 添加 Required reviewers；Deployment branches and tags 选 Selected branches and tags，仅添加 branch `main` |
| `crates-io` | 发布 crates.io 必需 | 同样添加审核人并仅允许 branch `main`；首次发布的 Secret 放在这里 |

平台绑定的 Environment 名称必须逐字匹配。即使 checkout 的代码来自 tag，工作流本身在 main
上手动运行，所以环境允许的是 branch `main`，不是 tag。若开启 Prevent self-review，需另一个审核人。

Secrets/Variables 清单：

| 项目 | 是否必需 | 在哪里、填什么 |
| --- | --- | --- |
| Environment secret `CRATES_IO_BOOTSTRAP_TOKEN` | 仅 crates.io 首次发布必需 | Settings → Environments → `crates-io` → Environment secrets → Add environment secret，值为下一节创建的令牌 |
| Repository secrets | 无需 | 不需要配置 `PYPI_API_TOKEN`、`TWINE_PASSWORD`、`GITHUB_TOKEN` 或额外的 `CARGO_REGISTRY_TOKEN` Secret |
| Repository / Environment Variables | 无需 | 此工作流没有要手动配置的 Variables |
| `GITHUB_TOKEN`、OIDC 相关运行时变量 | 无需手填 | GitHub 自动提供；`CARGO_REGISTRY_TOKEN` 仅在发布步骤中由工作流自动注入 |

不要把令牌写入文件、PR 或评论。若组织限制 Actions 使用，需要在组织/仓库 Actions 设置中允许
该流程所使用的 `actions/*`、`pypa/gh-action-pypi-publish`、`rust-lang/crates-io-auth-action`。
不需要把默认 Workflow permissions 改为仓库读写。

### 第三步：PyPI 首次即使用受信发布（无令牌）

用将持有此项目的 PyPI 账号登录并按平台要求启用双因素认证。
首次发布前打开 <https://pypi.org/manage/account/publishing/>，添加 GitHub pending publisher：

| 表单字段 | 准确值 |
| --- | --- |
| PyPI Project Name | `suye` |
| Owner | `sheng-ke-zhi` |
| Repository name | `suye` |
| Workflow name / filename | `release.yml`（不是完整路径，也不是 Actions 显示名称） |
| Environment name | `pypi` |

已有项目时，改用项目 **Manage → Publishing** 添加同样绑定。
pending publisher 在首次成功上传后自动转为正式绑定，**创建绑定本身不会占住包名**。
不需要生成 PyPI API token，也不需要配置 PyPI Secret。

### 第四步：crates.io 首次用一次性授权，之后使用受信发布

按当前官方限制，**首次创建 crate 仍需要 API token**，不能直接用 OIDC 创建新 crate。

1. 登录将持有此 crate 的 crates.io 账号，打开 <https://crates.io/settings/tokens> → New Token。
2. 名称可填 `suye-first-publish`；Expiration 选短有效期（例如 7 days）；
   Scopes 仅选择 `publish-new`（Publish new crates），Crates 的 name pattern 限制为 `suye`。
   无需 change-owners、yank、trusted-publishing 或 publish-update 权限。
3. 将令牌保存为上节 `crates-io` 环境里的 `CRATES_IO_BOOTSTRAP_TOKEN`。
   只在首次发布时选择 `crates_auth=bootstrap`，后续不再用这个令牌。
4. 首次发布成功后，打开 crate 页面 **Settings → Trusted Publishing → Add → GitHub**，填写：

| 字段 | 准确值 |
| --- | --- |
| Repository owner | `sheng-ke-zhi` |
| Repository name | `suye` |
| Workflow filename | `release.yml` |
| Environment | `crates-io` |

5. 保存绑定后撤销首次令牌，并删除 GitHub 环境中的 `CRATES_IO_BOOTSTRAP_TOKEN` Secret。
   后续使用默认的 `crates_auth=trusted`，工作流通过官方 Action 获取并自动撤销短期令牌。

### 第五步：第一次发布怎么点

1. 由人工审核并合并 PR，以及已确认许可证的修改。此交付不会主动合并或正式发布。
2. 完成两个 GitHub 环境、PyPI pending publisher、crates.io 首次令牌配置。
3. 从已审核 main 提交创建 `v0.1.0` tag。例如在 GitHub **Releases → Draft a new release**
   创建 tag `v0.1.0`，Target 选 `main` 后发布 GitHub Release；这一步不会上传包索引。
4. 打开 **Actions → Build and publish → Run workflow**，分支选 `main`，
   `tag=v0.1.0`，`target=both`，`publish` **不勾选**，`crates_auth=bootstrap`，先检查构建演练结果。
5. 确认许可证和发行归档内容后再运行同样参数，这次勾选 `publish`。
   构建及发布预检通过后，在运行详情中审核 `pypi` 和 `crates-io` 两个环境的部署。
6. 检查 PyPI/crates.io 上 `suye` 的版本均为 `0.1.0`，随后完成 crates.io 的受信发布绑定并撤销首次令牌。

两平台发布并非原子操作。若一边成功另一边失败，先排查失败原因，再选择 `target=pypi` 或
`target=crates` 只补发失败平台；不要重复上传已经成功的同版本。
后续版本创建新的 `vX.Y.Z` tag，`crates_auth=trusted`；不要移动已经发布的 tag。

政策：<https://peps.python.org/pep-0541/#invalid-projects>、<https://crates.io/policies>。
官方发布说明：<https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>、
<https://crates.io/docs/trusted-publishing>。
