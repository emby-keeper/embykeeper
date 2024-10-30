---
head:
  - - meta
    - name: description
      content: Embykeeper 是一个Emby 影视服务器签到保号的自动执行工具, 提供 TG 机器人签到和 Emby 服务器保活功能.
  - - meta
    - name: keywords
      content: Embykeeper, Emby, 签到, 保活, Telegram, 公益服
  - - meta
    - name: google-site-verification
      content: 2Rwsm1-SrtpbMLAgt249LnzWKqx2bbuNVuE-5LiU4dc

# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: 'Embykeeper'
  text: 'Emby 保号自动化'
  tagline: Emby 保活 + TG 签到
  image:
    src: /logo.webp
    alt: Embykeeper
  actions:
    - theme: brand
      text: Embykeeper 是什么?
      link: /guide/
    - theme: alt
      text: 快速安装
      link: /guide/安装指南
    - theme: alt
      text: 配置文档
      link: /guide/配置文件
    - theme: alt
      text: Github
      link: https://github.com/embykeeper/embykeeper

features:
  - icon:
      src: /emby.svg
      width: 28px
      wrap: true
    title: Emby 站点模拟观看
    details: 模拟登陆 Emby 公益站并观看一定时间, 适用于 N 天不登陆/观看即封禁的站点, 支持任意站点.
  - icon:
      src: /tg.svg
      width: 28px
      wrap: true
    title: Telegram 机器人每日签到
    details: 模拟在 Telegram 机器人每日签到, 已支持 50+ 站点.
  - icon: 🎟️
    title: 邀请码抢注
    details: 时刻关注站点邀请码发放或开注信息, 第一时间自动注册. 同时支持考核辅助.
  - icon: 🪐
    title: 支持云部署
    details: 支持 Huggingface 或 Render 免费云部署, 无需服务器, 支持网页管理.
  - icon: 🛡️
    title: 高稳定性
    details: 已持续开发改进 2 年, 签到和保号已尽可能与真人操作一致, 不容易被识别.
  - icon: 🔒
    title: 高安全性
    details: 代码开源, 不收集任何密钥和隐私数据.
---

<script setup>

import TerminalExampleSection from './components/TerminalExampleSection.vue'
import WebExampleSection from './components/WebExampleSection.vue'

</script>

<hr style="margin-top: 30px; margin-bottom: 30px;">

<TerminalExampleSection />

<hr style="margin-top: 30px; margin-bottom: 30px;">

<WebExampleSection />
