
# 全局规则

- 我本地已经配置了playwright mcp，但可能没有启动，需要使用时你自行先启动这个mcp，启动命令为：`~/shells/start-ai-chrome.sh` ,用的remote-debugging-port=9222方式
- vrs运维相关的知识库文件位于 `~/ai/agents/vrs_ops/AGENTS.md`，请读取该文件及引用文件内容做为你的知识库
- 由于相关知识和脚本我会在多台机器上同步，所以涉及到路径的地方，尽量用`~/` 这种相对用户目录的，而不是从根目录开始，我一般都是用的非root的用户，除非要做成系统服务等情况必须要用绝对路径时才可以用。
- 写脚本时也尽量考虑下多电脑的情况

# 本机环境

因此本文档我会同步到mac和linux机器，所以你自己根据当前的系统使用下面对应环境。

## linux (fan@fan-hp)

- 安装的miniconda ,位于 `~/miniconda3` ,里面我装了多个env,如python3.10 ， python 3.11等，优先用这里面的python环境，而不是系统的python环境。
- 已安装jdk8，并且java命令已经在path里面
- jdk11 位于 `/data/soft/jdk-11.0.19`
- jdk17 位于 `/data/soft/jdk-17.0.7`
- 本机已安装android studio，sdk位于 `~/Android`,比如adb命令位于`~/Android/Sdk/platform-tools/`下面

## mac

## macmini (weichaofan@weichaofan-mini)

