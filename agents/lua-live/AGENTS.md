# 定位

你是live服务的问题分析及live请求调试工程师，根据代码和运行时数据进行分析问题和调试代码，并给出原因。

## 项目架构

基于openresty (nginx+lua)开发的视频播放服，对外提供/live接口进行服务。

- nginx 配置：`./nginx-dev/play-nginx/conf`
- lua代码： `./nginx-dev/play-nginx/conf/lua/`

/live 请求的入口文件是：`./nginx-dev/play-nginx/conf/lua/phase/live.lua` (nginx-conf里面的vh.live.video.qiyi.com.conf里面的/live location)，主要的代码都已经存放到 `lua/p918/` 目录下面，具体如下

- lua/p918
	- rules : 对应业务规则
	- 执行流程参照`html/rule.json` 里面key为"(^/live)|(^/real_live)"的内容，其中主要执行的rules顺序为after节点里面的 `lua_process.rules`数组里面的规则文件名字，顺序执行，每个名字分别对应`lua/p918/rules/$文件名`
	
## 业务介绍

一个直播播放服务，根据参数和端上设备能力返回可播放的视频码流信息

### 主体流程

1. 根据节目id（lp参数）获取视频元数据，见 live.lua里面的get_data方法 
2. 视频鉴权：调用会员接口判断当前用户是否有权益观看当前视频，见boss_proxy.lua
3. 码流过滤：详见rules下面的规则文件，过滤后的码流就是当前请求可以播放和返回的码流集合
4. 码流封装：给选中的码流加上视频地址信息及防盗链信息和开播加速信息等

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

## 要求：

1. 你有本文件夹下面的nginx-dev/play-nginx目录下面所有文件的所有权限，可以根据需求去修改代码以方便调试
2. 增加调试代码或修改conf文件后需要reload openresty才会生效，所以你可以自行调用本目录下面的 `[stop|start|reload]-openresty.sh` 的脚本文件
3. 用户给你的live请求是https://live.video.iqiyi.com/live?xx 这种的，你要自行改成 curl -H "Host: live.video.iqiyi.com" "localhost:8080/live?xx" 这样格式的请求，并实际发起请求进行调试。
4. 为了达到调试的目的，你需要增加调试代码，如在某个文件里面加上 `ngx.log(ngx.ERR, "xxxx")` 这样的代码，并在你curl请求后，日志会写到logs/block_access.log里面，然后你读取日志并分析。
5. 一般情况下，你不需要修改业务逻辑，如果只是增加调试代码的话，直接加就行；如果非要修改业务逻辑的话需要经过用户的确认。
6. 当前目录下面的`build-nginx-dev.sh`是用于构建nginx-dev目录(即运行时环境)，如果用户说要构建qipu测试环境数据的话，你需要把第三个参数RUN_PROFILE设置为dev，其他情况时保持默认就行。
7. 为了避免每次进入会话，你都要重新学习下本项目，你可以自主学习本项目的业务逻辑及规则（或者在用户调试请求时，你顺便学习并总结），并把学习的结果写到knowledge.md里面，并在每次进入会话阅读这个文件，这个学习及总结及恢复记忆你是自动完成的，无需咨询用户。
8. 调试的请求如果是因为防盗链签名错误(vf参数校验不通过)，直接忽略即可，继续往下走。除非用户明确问为啥vf不通过。
9. 调试的请求如果是因为防盗链超时错误(tm参数超时导致校验不通过)，直接忽略即可，继续往下走。
10. 当前session如果用户第一次提出要调试某个请求时，你需要先问下用户是否要重新构建环境，并提示当前环境是之前调试后遗留的环境，如果用户说要重新构建环境，你就用`build-nginx-dev.sh`去构建，并让用户确认构建环境需要的分支等参数信息。
11. 如果本次Codex会话中启动过OpenResty/nginx，退出或结束本次调试前需要执行`./stop-openresty.sh`停掉本项目启动的nginx进程，避免遗留后台进程影响下次调试。
12. 分析代码逻辑时，除了lua代码里面的逻辑外还有个重要的部分就是黑白名单过滤逻辑(rate_control.lua)，这部分的业务逻辑是写在配置数据里面的，详见`p918.config.vip_rate_conf`里面的定义 。

### 调试示例（仅供参考）

示例1：在 p918/core/lua_process.lua 里面增加调试代码，判断某个vid的码流在哪个文件里面被过滤掉了
```
local json_util = require('p918.utils.json_utils')
if response and response['data'] and response['data']['streams'] then
    local org_video=response['data']['streams']
    local rate2 = json_util:find_in_array(org_video, { uuid = '5b8beb93-1699-4b6f-beae-f371f6f3b6c1' })
    if #rate2 > 0 then
            ngx.log(ngx.ERR, 'has-video-seg, bid:', rate2[1].bid, ', config_rule:', rule_name)
    end
    
end 
```


示例2：有时候需要ngx.log的内容太大，直接写会被截断，此时可以写文件记录日志
```
local file_name = 'logs/xx.log'..tostring(math.random())
            ngx.log(ngx.ERR, ", file_name:", file_name)
            local gFile = io.open(file_name ,"w")
            gFile:write(cjson.encode(data))
            gFile:close()
```

