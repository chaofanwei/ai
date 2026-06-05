# 根据需求 PMS 号查询备注

## 使用场景

用于根据需求 PMS 号查询该需求在 AllInTest/PMS 中的备注记录。

## 查询接口

接口固定使用 `GET` 请求：

```bash
curl -X GET "http://allintest.cloud.qiyi.domain:8081/allintest/pms_management/getAllCommentsByIssue?username=yanyanli&issue_key=VIDEODEV-$PMS_NUM"
```

其中 `$PMS_NUM` 替换为需求 PMS 号数字部分。

例如查询 PMS `5817` 的备注：

```bash
curl -X GET "http://allintest.cloud.qiyi.domain:8081/allintest/pms_management/getAllCommentsByIssue?username=yanyanli&issue_key=VIDEODEV-5817"
```

## 返回说明

接口返回 JSON，其中 `comments` 字段是备注数组。

`comments` 数组里的每个对象代表一条备注信息，通常包含：

- 备注时间
- 备注人
- 备注内容：`comment_body`
- 其他接口返回的备注相关字段

## 格式化查看

如果本机安装了 `jq`，可以格式化查看完整返回：

```bash
curl -sS -X GET "http://allintest.cloud.qiyi.domain:8081/allintest/pms_management/getAllCommentsByIssue?username=yanyanli&issue_key=VIDEODEV-5817" \
  | jq .
```

只查看备注数组：

```bash
curl -sS -X GET "http://allintest.cloud.qiyi.domain:8081/allintest/pms_management/getAllCommentsByIssue?username=yanyanli&issue_key=VIDEODEV-5817" \
  | jq '.comments'
```

提取每条备注的时间、人和内容：

```bash
curl -sS -X GET "http://allintest.cloud.qiyi.domain:8081/allintest/pms_management/getAllCommentsByIssue?username=yanyanli&issue_key=VIDEODEV-5817" \
  | jq -r '.comments[] | [.created, .author, .comment_body] | @tsv'
```

注意：不同接口版本返回的时间、人字段名可能不同。如果 `.created` 或 `.author` 为空，应先查看完整 JSON，再按实际字段名提取。


# 根据需求 PMS 号查询标题


## 查询标题接口

接口固定使用 `GET` 请求：

```bash
curl -X GET "http://allintest-pms.qiyi.domain:8082/pms/getOneIssueDetail?username=lizhen07&with_transition=0&issue_key=VIDEODEV-VIDEODEV-$PMS_NUM"
```

## 返回说明

接口返回 JSON，其中 `issue.summary` 字段就是标题。