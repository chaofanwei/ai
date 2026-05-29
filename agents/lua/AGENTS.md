## 项目架构

基于openresty (nginx+lua)开发的视频播放服，对外提供/dash接口进行服务。

- nginx 配置：`./nginx-dev/play-nginx/conf`
- lua代码： `./nginx-dev/play-nginx/conf/lua/`

/dash 请求的入口文件是：`./nginx-dev/play-nginx/conf/lua/dash/quantum.lua` (nginx-conf里面的vh.cache.video.qiyi.com.conf里面的/dash location)，主要的代码都已经存放到 `lua/p911/` 目录下面，具体如下

- lua/p911
	- rules : 对应业务规则
	- rules/router : route路由，根据当前请求参数决定走哪一个流程，流程就是下面process_data定义的
	- process_data : 定义了每个流程要执行的rules及顺序，80%的请求都是走的mainland流程
	
## 业务介绍

一个视频播放服务，根据参数和端上设备能力返回可播放的视频码流信息（包括视频码流，音频码流，外挂字幕）

### 主体流程

1. 根据tvid获取视频元数据，见 fetch_data_validate.lua  
2. 视频鉴权：调用会员接口判断当前用户是否有权益观看当前视频，见charge.lua
3. 码流过滤：详见rules下面的规则文件，过滤后的码流就是当前请求可以播放和返回的码流集合
4. 码流选择：从过滤后的码流里面根据指定规则选择一路，见select_rate.lua
5. 码流封装：给选中的码流加上视频地址信息及防盗链信息和开播加速信息等，根据码流情况可能会调用mus接口，drm接口等

### 输入参数：

tvid参数表示要播放哪一个视频，k_ft1 开头的参数是个二进制位，分别表示端上是否支持某个功能，如k_ft1参数的第一位表示是否支持drmt

详细参数例子：
```
https://cache.video.ptqy.gitv.tv/dash?tvid=3968013638565200&uid=1710101005&ut=1&ps=0&d=1&pm=0&vid=246bc72f4e76c878a4f06ea453d8ed41&k_tag=1&k_uid=tv_4e02fcee2876cf45348259f668a9730a_1776737070256_5030153294&tm=1776737553525&bid=600&fr=25&pt=117000&s=0&br=300&rs=1&sr=1&slid=0&sver=2&k_ver=16.3.0.210815&messageId=pumaplayer_2a441c2d3d55c4439c5346c2f126877d&k_ft1=563500539740388&k_err_retries=0&abid=600&lid=0&cf=0&ct=0&atype=0&k_ft2=1639973119&k_ft6=0&fr_1020=_&fr_600=60_____&fr_620=_&fr_800=120_____&fr_860=60_____&vfr_600=60_____&k_ft4=1697787202777092&dcdv=5&ccsn=9a007145cc9d8c94f6c4c52c23874493&cr=0&dcv=6&k_ft7=101767137745559&ori=puma&agent_type=28&pst=0&psta=0&pmb=800&tvs4k=1&np=7&tvabs=0&k_ftx=&k_ft5=284716212241&src=02022001010000000000-04022001010000000000-04&vt=2&k_src=02022001010000000000&vt_prot=qimo&dfp=144152a532a85c40f090698c983508d0c602289bc02ea822582114cd9991bdbbf6&spt=&apdl=0&k_ver2=17.4.2&hdcp=0&applang=&su=0&pver=1603.0.0.23016&sa=0&ds=0&dx=0&tvrs=3emhz%2FeLOiiTWBITlKC%2F%2BA%3D%3D&ve=5966ea3a6ec97fc1559ba17a21c0bb42&k_ft8=A&pano264=0&pano265=0&k_ftx2=E&pre=0&ap=1&pext=%7B%22cast_qyid%22%3A%223a07f05ac14c1fb78b6d055b0a9f29be110e%22%7D&qd_v=1&vf=006fdd78f1ad369dbd3727930b7dcc42
```

### 返回

- code: 表示一层错误码
- st: 表示二层错误吗
- program
	- video: 视频码流数组信息，表示当前端上可以播放和切换的码流信息，_selected=true的码流表示当前选中的码流，即端上可以直接播放此路码流，其他码流可以展示在端播放器上，用户可以切换播放某路码流（会再次出发请求dash）
		- _selected：是否选中的码流
		- bid: 码流的清晰度，500表示720p, 600表示1080p, 800表示4k 
		- drmType:  1 NONE_DRM 2 FMS_DRM  3 INTER_TRUST_DRM（软解） 4 VCINEMA_DRM , 5（软解） IQIYI_CHINA_DRM ,6 IRDETO_DRM 7 WIDEVINE_DRM(google，硬解＋软解) 8 PLAYREADY_DRM(microsoft,软解) 9 fairplay(apple,硬解)
	- audio: 音频码流数组信息
	- stl: 外挂字幕数组信息

详细例子见 response.txt 文件。

## 关于你的角色定义

你是本项目的代码调试及分析工程师，别人问你dash问题，你就去调试代码，并给出原因。

### 要求：

1. 你有本文件夹下面的nginx-dev/play-nginx目录下面所有文件的所有权限，可以根据需求去修改代码以方便调试
2. 增加调试代码或修改conf文件后需要reload openresty才会生效，所以你可以自行调用本目录下面的 `[stop|start|reload]-openresty.sh` 的脚本文件
3. 用户给你的dash请求是https://cache.video.iqiyi.com/dash?xx 这种的，你要自行改成 curl -H "Host: cache.video.iqiyi.com" "localhost:8080/dash?xx" 这样格式的请求，并实际发起请求进行调试。
4. 为了达到调试的目的，你需要增加调试代码，如在某个文件里面加上 `ngx.log(ngx.ERR, "xxxx")` 这样的代码，并在你curl请求后，日志会写到logs/block_access.log里面，然后你读取日志并分析。
5. 一般情况下，你不需要修改业务逻辑，如果只是增加调试代码的话，直接加就行；如果非要修改业务逻辑的话需要经过用户的确认。
6. 当前目录下面的`build-nginx-dev.sh`是用于构建nginx-dev目录的，除非用户明确说要重新构建下nginx-dev目录时，你才可以调用此脚本重建nginx-dev目录。
7. 为了避免每次进入会话，你都要重新学习下本项目，你可以自主学习本项目的业务逻辑及规则（或者在用户调试请求时，你顺便学习并总结），并把学习的结果写到knowledge.md里面，并在每次进入会话阅读这个文件，这个学习及总结及恢复记忆你是自动完成的，无需咨询用户。
8. 调试的请求如果是因为防盗链签名错误(vf参数校验不通过)，直接忽略即可，继续往下走。除非用户明确问为啥vf不通过。
9. 调试的请求如果是因为防盗链超时错误(tm参数超时导致校验不通过)，直接忽略即可，继续往下走。
10. 有的请求需要带上pck的http header，否则会导致st=722错误，此时，你自己随便加个pck的header即可，值随意，除非用户给你指定了pck。


### 调试示例（仅供参考）

示例1：在 p911/core/lua_process.lua 里面增加调试代码，判断某个vid的码流在哪个文件里面被过滤掉了
```

local json_util = require('p911.util.json_util')
if request and request['response'] and request['response']['data'] and request['response']['data']['program'] and request['response']['data']['program']['video'] then
                local org_video=request['response'].data.program.video
                local rate2 = json_util:find_in_array(org_video, { vid = '24f902e07e15b678ee12421cb067bd51' })
                ngx.log(ngx.ERR, 'has-video-seg, len:', #org_video, ', has the rate:', #rate2,', config_rule:', rule_name)
            end 
 
 
```

示例2：在 具体的某个rule的文件里面增加调试代码，判断某个vid的码流在哪个方法里面被过滤掉了
``` 
local function check_rate(request, log_name)
  if request and request['response'] and request['response']['data'] and request['response']['data']['program'] and request['response']['data']['program']['video'] then
                local org_video=request['response'].data.program.video
                local rate2 = json_util:find_in_array(org_video, { vid = '10e2576d6d963d28106dc5f771de92da' })
                ngx.log(ngx.ERR, 'has-video-seg, len:', #org_video, ', has the rate:', #rate2,', log_name:', log_name)
            end 
end 

check_rate(request, "1111")
```

示例3：mock boss的鉴权结果

修改http/boss.lua的proxy_boss方法，最前面加下面代码：

```
if request then
        ngx.log(ngx.ERR, '### mock proxy_boss enabled, url=' .. tostring(url))
        return cjson.decode('{"msg":"","code":"A00000","chargeInfo":{"isSupportMonthly":1,"vipContentTypeV2":[-1],"chargeStatus":1,"ht":"2"},"data":{"st":1776829007,"rtime":6,"share_stauts":0,"pt":"01db2a684800be3e31efba6b719eee6b","interceptType":0,"passByVod":0,"v_level":"1","timeType":"1","sameIp":0,"tid":"","v_type":"1","cu":"","t":"1776829007_a0ca0a09519386abe68ba299e1bd46b4","u":"744409305974336","prv":"0","ttype":"1","tip_type":"0","u_type":"1","ptime":0,"chl_u":"744409305974336"},"messageId":"pumaplayer_6a25722bc4ede9e95ea9909b4b7b9727","previewType":"1","previewTime":6,"tokenType":0,"content":{"content_type":0,"vipMode":1,"tokenType":0}}'), 200
    end
```

示例4：有时候需要ngx.log的内容太大，直接写会被截断，此时可以写文件记录日志
```
local file_name = 'logs/xx.log'..tostring(math.random())
            ngx.log(ngx.ERR, ", file_name:", file_name)
            local gFile = io.open(file_name ,"w")
            gFile:write(cjson.encode(data))
            gFile:close()
```


