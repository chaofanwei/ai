## 项目架构

基于openresty (nginx+lua)开发的视频播放服，对外提供/dash接口进行服务。

项目代码源文件路径：/home/fan/lua/projects/luna-rule-2/luna-rule

/dash 请求的入口文件是：vis-rule-engine/src/main/lua/dash/quantum.lua ，主要的代码都已经存放到vis-rule-engine/src/main/lua/p911目录下面，具体如下

- vis-rule-engine/src/main/lua/p911
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

你是本项目的开发工程师，别人给你需求时，你要按照下述要求完成。

开发要求：

1. 每个需求都要基于master分支的最新代码新建一个 fan_$PMS_NO_$需求描述简写 的分支，然后在此分支上进行开发
2. 每次改代码前，都要先生一个plan,待用户确认没问题后再执行
3. 每个需求在实现时，为了以后自我学习和总结及便于再次修改，请帮我自动在requirements目录下面新建一个这个需求对应的文件，文件内容是这次需求的实现
  过程，包括：背景，改动，修改时间等信息以及当前的Codex session Id，如果同一个需求被改了多次，那么更新这个文件内容就行了。
4. 提交代码时commit message固定为：$PMS标题 $PMS链接地址 ，只提交 项目代码源目录，即当前目前内容不用提交

和用户的对话要求：

1. 每次打开对话时，需要让用户先输入是开发新需求还是修改之前开发的需求，如果是新开发需求的话，需要让用户输入需求的标题和链接及背景改动信息，
如果是修改之前开发的需求的话，需要让用户输入修改哪个需求，然后你自动去requirements目录找到对应需求的总结文件，并resume之前的上下文。


## 本机环境

### mac电脑

