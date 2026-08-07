## 项目架构

基于openresty (nginx+lua)开发的直播播放服务，对外提供/live接口进行服务，主要包含代码和nginx-conf。

项目lua代码源文件路径：~/lua/projects/live-luna/live-luna-rule
项目nginx-conf路径：~/lua/projects/live-luna/nginx-config

/live 请求的入口文件是：vis-rule-engine/src/main/lua/phase/live.lua ，主要的代码都已经存放到vis-rule-engine/src/main/lua/p918目录下面，具体如下

- vis-rule-engine/src/main/lua/p918
	- rules : 对应业务规则
	
nginx-conf 里面目前有用就是nginx1文件夹(比如/live的location就在`vh.live.video.qiyi.com.conf`里面)，其他的文件夹可以忽略。
	
	
## 业务介绍

一个直播播放服务，根据参数和端上设备能力返回可播放的视频码流信息

### 主体流程

1. 根据节目id（lp参数）获取视频元数据，见 live.lua里面的get_data方法 
2. 视频鉴权：调用会员接口判断当前用户是否有权益观看当前视频，见boss_proxy.lua
3. 码流过滤：详见rules下面的规则文件，过滤后的码流就是当前请求可以播放和返回的码流集合
4. 码流封装：给选中的码流加上视频地址信息及防盗链信息和开播加速信息等

live接口的执行流程参照`src/main/rule.json` 的2746行到2835行的json内容，其中主要执行的rules顺序为after节点里面的 `lua_process.rules`数组里面的规则文件名字，顺序执行，每个名字分别对应`src/main/lua/p918/rules/$文件名`

### 输入参数：

lp参数表示要播放哪一个视频，k_ft1 开头的参数是个二进制位，分别表示端上是否支持某个功能，如k_ft1参数的第一位表示是否支持drmt

详细参数例子：
```
https://live.video.iqiyi.com/live?lp=7990073197087723&src=01010031010000000000&uid=4457283341851136&rateVers=PC_QIYI_3&k_uid=f1a8efb491e58a6c018835c33a290048&dfp=a11c2b46bbd357484a8dc3eef254853f7d838010f1997c3e45494e327eb08ed0be&ve=4b5d
5601ce4bbcd23289cb24bcc64ac6&k_err_retries=0&pck=cb3sDD8VHNEGb9wtODGwT1Om1DTQszH2gByAlfEbSv7AgHWbiDaTHvqfrvE1t7i5snZ18&cid=afbe8fd3d73448c9&agenttype=1&qc5=f1a8efb491e58a6c018835c33a290048&play_v=playerzt1.0&platform=97ae2982356f69d8&ckVersion=11.0&messageId=livePlayerH5S
H_75DF525B2BEE527EAB1806FFB54670EE&sr=1&tm=1780302871&ori=pcw&qd_v=5&qdy=a&qds=0&k_ft2=0&k_ft1=141287244170240&k_ft4=459046104858849&vf=2495c14eddacd8c6a91b6068bd26b3f3
```

### 返回

- code: 表示一层错误码
- st: 表示二层错误吗
- data
	- streams: 视频码流数组信息，表示当前端上可以播放和切换的码流信息
		- bid: 码流的清晰度，500表示720p, 600表示1080p, 800表示4k 
		- drmType:  1 NONE_DRM 2 FMS_DRM  3 INTER_TRUST_DRM（软解） 4 VCINEMA_DRM , 5（软解） IQIYI_CHINA_DRM ,6 IRDETO_DRM 7 WIDEVINE_DRM(google，硬解＋软解) 8 PLAYREADY_DRM(microsoft,软解) 9 fairplay(apple,硬解)

详细例子见 response.txt 文件。

## 关于你的角色定义

你是本项目的开发工程师，别人给你需求时，你要按照下述要求完成。

开发要求：

1. 每个需求都要基于master分支的最新代码新建一个 fan_$PMS_NO_$需求描述简写 的分支，然后在此分支上进行开发；PMS_NO只保留数字，不带VIDEODEV-前缀
2. 每次改代码前，都要先生一个plan,待用户确认没问题后再执行
3. 每个需求在实现时，为了以后自我学习和总结及便于再次修改，请帮我自动在requirements目录下面新建一个这个需求对应的文件，文件内容是这次需求的实现
  过程，包括：背景，改动，修改时间等信息以及当前的Codex session Id，如果同一个需求被改了多次，那么更新这个文件内容就行了。
4. 提交代码时commit message固定为：$PMS标题 $PMS链接地址 ，只提交 项目代码源目录，即当前目前内容不用提交
5. 每次都是最小化代码改动
6. 用户确认没问题后在提交代码，你不要擅自提交及push代码
7. 用户明确要求提交并 push，且远端推送成功后，需要自动给对应 PMS 增加一条开发完成备注。备注必须包含开发分支、Commit、改动说明和验证结果，并使用下面约定的格式。

### PMS 开发完成备注

调用下面的接口给 PMS 增加备注：

```bash
curl --request POST \
    'http://allintest.cloud.qiyi.domain/allintest/pms_management/addIssueComment' \
    --header 'Content-Type: application/json;charset=utf-8' \
    --data '{
      "author": "vrs_service",
      "issue_key": "VIDEODEV-12345",
      "comment_text": "这里填写 PMS 备注内容"
    }'
```

其中 `issue_key` 替换为当前需求的 PMS 编号，`comment_text` 固定按以下格式组织，并替换其中的实际内容：

```text
开发已完成并推送。
开发分支：fan_$PMS_NO_$需求描述简写
Commit：本次提交的短 commit id
改动说明：概括本次实际改动及影响范围。
验证结果：填写本次实际执行的测试及结果。
```

例如：

```text
开发已完成并推送。
开发分支：fan_5897_xinai_boss_status
Commit：b76f6e222
改动说明：仅新爱小屏 src 白名单请求根据新爱鉴权 chargeStatus 同步 bossStatus（付费=2，免费=0），其他鉴权链路保持不变。
验证结果：定向单测 7 successes / 0 failures。
```

接口返回 `code=A00000` 后才算备注成功；最终回复用户时需要说明 PMS 备注已添加，并给出返回的 `comment_id`。如果接口失败，需要明确告知用户失败信息，不得声称备注成功。

和用户的对话要求：

1. 每次打开对话时，需要让用户先输入是开发新需求还是修改之前开发的需求，如果是新开发需求的话，需要让用户输入需求的标题和链接及背景改动信息，
如果是修改之前开发的需求的话，需要让用户输入修改哪个需求，然后你自动去requirements目录找到对应需求的总结文件，并resume之前的上下文。
2. 如果用户要diff或者commit , push之类的话，默认只给修改的代码的改动就行，不用给本目录下面的requirements的改动。
