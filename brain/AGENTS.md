
# 全局规则

- 本地已经配置了playwright mcp，但可能没有启动，需要使用时你自行先启动这个mcp，启动命令为：`~/shells/start-ai-chrome.sh` ,用的remote-debugging-port=9222方式
- vrs运维相关的知识库文件位于 `~/ai/agents/vrs_ops/AGENTS.md`，请读取该文件及引用文件内容做为你的知识库
- 由于相关知识和脚本我会在多台机器上同步，所以涉及到路径的地方，尽量用`~/` 这种相对用户目录的，而不是从根目录开始，我一般都是用的非root的用户，除非要做成系统服务等情况必须要用绝对路径时才可以用。
- 写脚本时也尽量考虑下多电脑的兼容情况
- 为了解决多个电脑上命令位置不一致的问题，你建了个`~/ai/shells/init.sh` 这个文件里面根据机器环境信息分别设置同一个变量的不同值。你可以在你的脚本里面用`source ~/ai/shells/init.sh` 来加载这个文件，然后就可以根据里面的变量来做不同的操作了。 当然你也可以修改这个文件，在里面添加你自己电脑的特定配置。
- sudo 需要交互式密码，改用系统的 pkexec 授权弹窗来执行以便我输入密码
- 本项目下执行sh脚本文件，python文件等默认使用沙箱外执行，即调用工具时必须设置 `sandbox_permissions=require_escalated`。包括但不限于：执行 Python、pip/包管理器、网络请求或诊断命令（如 curl、ping、nc、dig、nslookup）、查看本机信息或进程端口命令（如 ps、netstat、ss、lsof）等。
- 你在奇智平台上的个人访问密钥为：claude-code-weichaofan|195796607|db87328fd62dfeca71085c13c8f5f7cc
# 常用工具

- 发送微信通知消息给我的工具：`http://myroute.cn/msg?echostr=xxx` ,其中`echostr`参数的内容就是你想要发送的消息内容，支持以`\n`换行(但最多支持5行，每行最多40个文字长度)，注意参数要urlencode编码.
- 其他全局技能(skill)，请自行阅读 `~/ai/brain/skills/` 目录里面的文件(包括子目录)。
- 不要随意阅读`~/ai/agents/`下面的内容，除非当前目录是`~/ai/agents/$XX` 时，你才可以阅读$XX 目录下的内容 ，但也只能读`~/ai/agents/`下面$XX目录的内容
- 本机已经安装飞书cli (lark-cli, lurk-cli) ,位置在`/home/fan/.npm-global/bin/lark-cli` ，用于读取或编辑飞书云文档等
# 机器环境

因此本文档我会同步到mac和linux机器，所以你自己根据当前的系统使用下面对应环境。

## linux (fan@fan-hp)

- 安装的miniconda ,位于 `~/miniconda3` ,里面我装了多个env,如python3.10 ， python 3.11等，优先用这里面的python环境，而不是系统的python环境。
- 已安装jdk8，并且java命令已经在path里面
- jdk11 位于 `/data/soft/jdk-11.0.19`
- jdk17 位于 `/data/soft/jdk-17.0.7`
- 本机已安装android studio，sdk位于 `~/Android`,比如adb命令位于`~/Android/Sdk/platform-tools/`下面

## mac （weichaofan@wcfMac-Air）

- 安装的miniconda ,位于 `~/miniconda3` ,里面我装了多个env,如python310 ,优先用这里面的python环境，而不是系统的python环境。
- 已安装jdk8，并且java命令已经在path里面
- jdk17 位于 `/Library/Java/JavaVirtualMachines/jdk-17.0.15.jdk/Contents/Home/` , 比如java命令位于这个目录下面
- 系统里面已经安装了ffmpeg命令
- 本机已安装android studio，sdk位于 `~/Library/Android/sdk/`,比如adb命令位于`~/Library/Android/sdk/platform-tools/`下面


## macmini (weichaofan@weichaofan-mini)

- 安装的miniconda ,位于 `~/miniconda3` ,里面我装了多个env,如python3.11 ,优先用这里面的python环境，而不是系统的python环境。
- 本机已安装android studio，sdk位于 `~/Library/Android/sdk/`,比如adb命令位于`~/Library/Android/sdk/platform-tools/`下面
- 系统里面已经安装了ffmpeg命令
- 已安装jdk8，并且java命令已经在path里面,路径为：`/Library/Java/JavaVirtualMachines/zulu-8.jdk/Contents/Home`
- jdk17 位于 `/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home` , 比如java命令位于这个目录下面

