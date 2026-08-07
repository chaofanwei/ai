# 使用说明

## 克隆仓库

本仓库依赖多个 git submodule（各 agent 引用的业务代码仓库）。首次克隆请使用：

```bash
git clone --recurse-submodules <仓库地址>
```

已克隆但未拉取 submodule 时：

```bash
git submodule update --init --recursive
```

更新 submodule 到主仓库记录的版本：

```bash
git submodule update --recursive
```

`agents/lua/nginx-dev/play-nginx/` 由 `build-nginx-dev.sh` 本地构建生成，已 gitignore；`agents/play_ops/temp/` 下的 nginx 副本为本地临时目录，未纳入 submodule。

## brain文件夹

全局的知识库，各个agent都会读取，如codex, claude, cursor-agent

- 里面的AGENTS.MD 是入口

### claude 引用方法

`vim ~/.claude/CLAUDE.md` ： 请先阅读：`~/ai/brain/AGENTS.md`

### Cursor

`vim ~/.cursor/rules/global.mdc` ： 请先阅读：`~/ai/brain/AGENTS.md`

### codex

`vim ~/.codex/AGENTS.md` ： 请先阅读：`~/ai/brain/AGENTS.md`

## agents

存放不同功能的agent

### dash

开发新需求和分析dash功能，开发时会自动根据pms号建分支等

使用方法：直接说：我有个新需求 《需求标题》pms为 VIDEO-DEV-XXX，需求背景为xxxx, 期望的新功能为：xxx ,帮我实现下

### release_manager

每周的上线申请自动整理和打开浏览器自动填写表单，但是不会自动确认，需要你自己点击页面的确认

使用方法：先复制下狂飙里面每周上线里面的“查看上线内容”按钮弹窗里面的内容，然后说，下面是下周要上线的需求，帮我处理下，然后粘贴内容

### starmap

星图运维工程师，处理星图系统的问题，如改巡检的报警阈值

使用方法：直接粘贴巡检报警邮件的报警项的截图，然后说改下阈值到多少

### vrs_ops

vrs运维知识库，本地方主要是负责增删改知识库，另外全局知识库读取该知识库作为全局知识
